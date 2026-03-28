import os
import requests
import pytz
from dotenv import load_dotenv
load_dotenv()
from datetime import datetime, timedelta
from extensions import db
from models import Token, ServiceCenter, User

IST = pytz.timezone('Asia/Kolkata')


def get_ist_now():
    """Get current time in UTC (for database storage)

    IMPORTANT: This returns UTC time for database storage.
    All database DateTime fields store UTC only.
    Convert to IST only when displaying to users.
    """
    return datetime.utcnow()


def get_ist_now_aware():
    """Get current time as timezone-aware IST datetime for calculations"""
    return datetime.now(IST)


def ist_to_utc(ist_time):
    """Convert IST datetime to UTC for database storage"""
    if not ist_time:
        return None
    if ist_time.tzinfo is None:
        ist_time = IST.localize(ist_time)
    return ist_time.astimezone(pytz.utc).replace(tzinfo=None)


def utc_to_ist(utc_time):
    """Convert UTC datetime to IST - SINGLE SOURCE OF TRUTH for timezone conversion

    This is the ONLY function that should be used to convert UTC to IST.
    Use this in:
    - Templates (via Jinja filter)
    - API responses
    - Email notifications
    - Any user-facing datetime display

    Args:
        utc_time: datetime object from database (UTC, timezone-naive)

    Returns:
        datetime object in IST timezone (timezone-aware)
    """
    if not utc_time:
        return None

    # Database stores naive UTC - localize as UTC first, then convert to IST
    if utc_time.tzinfo is None:
        return pytz.utc.localize(utc_time).astimezone(IST)
    else:
        # Already timezone-aware - just convert to IST
        return utc_time.astimezone(IST)


def get_active_token_for_user(user_id):
    try:
        return Token.query.filter_by(user_id=user_id).filter(
            Token.status.in_(['PendingPayment', 'Active', 'Serving'])
        ).first()
    except:
        return None


def get_queue_count(center_id):
    try:
        return Token.query.filter_by(service_center_id=center_id, status='Active', is_walkin=False).count()
    except:
        # Fallback if is_walkin column doesn't exist
        return Token.query.filter_by(service_center_id=center_id, status='Active').count()


def get_serving_token(center_id):
    try:
        return Token.query.filter_by(service_center_id=center_id, status='Serving', is_walkin=False).first()
    except:
        # Fallback if is_walkin column doesn't exist
        return Token.query.filter_by(service_center_id=center_id, status='Serving').first()


def get_walkin_queue_count(center_id):
    try:
        return Token.query.filter_by(service_center_id=center_id, status='Active', is_walkin=True).count()
    except:
        return 0


def get_walkin_serving_token(center_id):
    try:
        return Token.query.filter_by(service_center_id=center_id, status='Serving', is_walkin=True).first()
    except:
        return None


def generate_token_number(center_id):
    today = get_ist_now().date()
    count = Token.query.filter(
        Token.service_center_id == center_id,
        db.func.date(Token.created_time) == today
    ).count()
    return f"T{count + 1:03d}"


def calculate_wait_time(center_id, token_position):
    """Calculate wait time until service starts (in minutes)"""
    center = ServiceCenter.query.get(center_id)
    # If first in queue, service starts immediately
    if token_position <= 1:
        return 0
    # For others: (position - 1) × avg service time
    wait_minutes = (token_position - 1) * center.avg_service_time
    # Cap maximum wait time at 3 hours (180 minutes)
    return min(wait_minutes, 180)


def get_traffic_multiplier():
    """Get traffic multiplier based on current time (IST)"""
    current_time = get_ist_now_aware()
    hour = current_time.hour

    # Peak hours: 9-11 AM and 4-8 PM (×2.0)
    if (9 <= hour < 11) or (16 <= hour < 20):
        return 2.0
    # Night hours: 10 PM - 6 AM (×1.5)
    elif hour >= 22 or hour < 6:
        return 1.5
    # Normal hours: rest of the day (×1.8)
    else:
        return 1.8


def calculate_travel_time(user_lat, user_lon, center_lat, center_lon):
    """Calculate travel time using ORS API + smart traffic adjustment"""
    if not all([user_lat, user_lon, center_lat, center_lon]):
        print("⚠️ Missing coordinates for travel time calculation")
        return None

    ors_api_key = os.getenv('OPENROUTESERVICE_API_KEY', '')
    if not ors_api_key:
        print("❌ ORS API key not configured")
        return None

    try:
        url = 'https://api.openrouteservice.org/v2/directions/driving-car'
        headers = {'Authorization': ors_api_key}
        body = {'coordinates': [[user_lon, user_lat], [center_lon, center_lat]]}

        response = requests.post(url, json=body, headers=headers, timeout=15)

        if response.status_code == 200:
            data = response.json()
            base_duration_seconds = data['routes'][0]['summary']['duration']
            base_time_minutes = base_duration_seconds / 60

            # Apply traffic multiplier
            traffic_multiplier = get_traffic_multiplier()
            adjusted_time_minutes = round(base_time_minutes * traffic_multiplier)

            current_time = get_ist_now_aware()
            print(f"✅ ORS + Traffic Adjustment:")
            print(f"   Base time: {base_time_minutes:.1f} min")
            print(f"   Time: {current_time.strftime('%I:%M %p')} (Hour: {current_time.hour})")
            print(f"   Traffic multiplier: {traffic_multiplier}x")
            print(f"   Adjusted time: {adjusted_time_minutes} min")

            return adjusted_time_minutes
        else:
            print(f"❌ ORS API error {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ ORS API exception: {e}")
        return None


def get_user_location(user):
    """Safely get user location, handling missing columns"""
    try:
        return getattr(user, 'latitude', None), getattr(user, 'longitude', None)
    except:
        return None, None


def expire_old_tokens():
    """Automatically expire tokens that are past their grace period"""
    current_time_utc = get_ist_now()  # UTC for DB comparison
    current_time_aware = get_ist_now_aware()  # IST aware for timezone comparisons

    # Expire pending payment tokens after 2 hours
    expiry_time = current_time_utc - timedelta(hours=2)
    expired_tokens = Token.query.filter(
        Token.status == 'PendingPayment',
        Token.created_time < expiry_time
    ).all()
    for token in expired_tokens:
        token.status = 'Expired'
        token.no_show_reason = 'Payment timeout'
        token.no_show_time = current_time_utc

    # Auto-expire late users (15 min grace period after expected arrival)
    active_tokens = Token.query.filter(Token.status == 'Active').all()
    for token in active_tokens:
        if token.reach_time:
            # Convert UTC reach_time to IST for comparison
            reach_time_ist = utc_to_ist(token.reach_time)

            # Auto-expire if > 15 min past expected arrival
            if current_time_aware > (reach_time_ist + timedelta(minutes=15)):
                token.status = 'Expired'
                token.no_show_reason = 'Auto-expired: Did not arrive within 15 minutes of expected time'
                token.no_show_time = current_time_utc
                print(f"⏰ Auto-expired token {token.token_number} - Expected: {reach_time_ist.strftime('%I:%M %p')}, Current: {current_time_aware.strftime('%I:%M %p')}")

    if expired_tokens or any(t.status == 'Expired' for t in active_tokens):
        db.session.commit()
        print(f"✅ Expired {len(expired_tokens)} pending + {sum(1 for t in active_tokens if t.status == 'Expired')} late tokens")


def recalculate_queue_times(center_id):
    """Recalculate estimated times for all active tokens after cancellation/skip"""
    try:
        center = ServiceCenter.query.get(center_id)
        if not center:
            print(f"❌ Center {center_id} not found")
            return

        current_time = get_ist_now()

        # Get all active tokens sorted by ID (booking order)
        active_tokens = Token.query.filter_by(
            service_center_id=center_id,
            status='Active',
            is_walkin=False
        ).order_by(Token.id).all()

        if not active_tokens:
            return

        # Check if there's a serving token
        serving_token = get_serving_token(center_id)

        if serving_token and serving_token.actual_service_end:
            # Counter busy, start from when it becomes free
            service_end_time = utc_to_ist(serving_token.actual_service_end)
        else:
            # Counter free now
            service_end_time = current_time

        # Recalculate for each token
        for token in active_tokens:
            try:
                user = User.query.get(token.user_id)
                if not user:
                    continue

                user_lat, user_lon = get_user_location(user)
                travel_time = calculate_travel_time(user_lat, user_lon, center.latitude, center.longitude)

                if travel_time is None:
                    print(f"❌ Cannot recalculate token {token.id} - travel time API failed")
                    continue

                # Earliest possible arrival
                earliest_leave = token.created_time + timedelta(minutes=10)
                earliest_arrival = earliest_leave + timedelta(minutes=travel_time)

                # Reach time = max(counter free, earliest arrival)
                reach_time = max(service_end_time, earliest_arrival)
                leave_time = reach_time - timedelta(minutes=travel_time)

                # Update token
                token.leave_time = leave_time
                token.reach_time = reach_time
                token.estimated_service_start = reach_time
                token.estimated_service_end = reach_time + timedelta(minutes=center.avg_service_time)

                # Next token starts after this one ends
                service_end_time = token.estimated_service_end
            except Exception as e:
                print(f"❌ Error recalculating token {token.id}: {e}")
                continue

        db.session.commit()
        print(f"✅ Recalculated {len(active_tokens)} tokens for center {center_id}")
    except Exception as e:
        print(f"❌ Error in recalculate_queue_times: {e}")
        db.session.rollback()


def send_reset_email(email, reset_link, user_type="User"):
    """Send password reset email using Brevo API (free 300 emails/day)"""
    print(f"🔐 Attempting to send email to {email}")

    # Brevo (formerly Sendinblue) - Free tier: 300 emails/day, no credit card
    brevo_api_key = os.getenv('BREVO_API_KEY', '')
    brevo_sender_email = os.getenv('BREVO_SENDER_EMAIL', 'queueflowqms@gmail.com')

    if brevo_api_key:
        try:
            response = requests.post(
                "https://api.brevo.com/v3/smtp/email",
                headers={
                    "api-key": brevo_api_key,
                    "Content-Type": "application/json"
                },
                json={
                    "sender": {"name": "QueueFlow", "email": brevo_sender_email},
                    "to": [{"email": email}],
                    "subject": "QueueFlow - Password Reset Request",
                    "htmlContent": f"""
                    <html>
                      <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                        <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                          <h2 style="color: #2DD4BF;">Password Reset Request</h2>
                          <p>Hello,</p>
                          <p>You requested to reset your password for your QueueFlow {user_type} account.</p>
                          <p>Click the button below to reset your password:</p>
                          <div style="text-align: center; margin: 30px 0;">
                            <a href="{reset_link}" style="background-color: #2DD4BF; color: #0F172A; padding: 12px 30px; text-decoration: none; border-radius: 5px; display: inline-block; font-weight: bold;">Reset Password</a>
                          </div>
                          <p>Or copy and paste this link into your browser:</p>
                          <p style="word-break: break-all; color: #666;">{reset_link}</p>
                          <p><strong>This link will expire in 1 hour.</strong></p>
                          <p>If you didn't request this, please ignore this email.</p>
                          <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">
                          <p style="color: #999; font-size: 12px;">QueueFlow - Smart Queue Management Platform</p>
                        </div>
                      </body>
                    </html>
                    """
                },
                timeout=10
            )
            if response.status_code == 201:
                print(f"✅ Email sent via Brevo to {email}")
                return True
            else:
                print(f"❌ Brevo error: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"❌ Brevo failed: {e}")

    # Fallback: Show reset link in console
    print(f"⚠️ Email service not configured. Reset link: {reset_link}")
    return False


def send_timing_alert(email, user_name, token_number, center_name, leave_time, reach_time):
    """Send timing alert email using Brevo API"""
    brevo_api_key = os.getenv('BREVO_API_KEY', '')
    brevo_sender_email = os.getenv('BREVO_SENDER_EMAIL', 'queueflowqms@gmail.com')

    if not brevo_api_key:
        print("⚠️ Brevo API key not configured")
        return False

    # Convert to IST using centralized helper
    leave_time = utc_to_ist(leave_time)
    reach_time = utc_to_ist(reach_time)

    try:
        response = requests.post(
            "https://api.brevo.com/v3/smtp/email",
            headers={
                "api-key": brevo_api_key,
                "Content-Type": "application/json"
            },
            json={
                "sender": {"name": "QueueFlow", "email": brevo_sender_email},
                "to": [{"email": email}],
                "subject": f"QueueFlow - Token {token_number} Timing Alert",
                "htmlContent": f"""
                <html>
                  <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                      <h2 style="color: #10B981;">✅ Token Confirmed!</h2>
                      <p>Helerlo {user_name},</p>
                      <p>Your token has been confirmed at <strong>{center_name}</strong>.</p>

                      <div style="background: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0;">
                        <h3 style="color: #2DD4BF; margin-top: 0;">Token Details</h3>
                        <p style="font-size: 24px; font-weight: bold; color: #333; margin: 10px 0;">Token: {token_number}</p>
                        <p style="margin: 5px 0;"><strong>Service Center:</strong> {center_name}</p>
                      </div>

                      <div style="background: #fff3cd; padding: 15px; border-left: 4px solid #ffc107; margin: 20px 0;">
                        <h3 style="color: #856404; margin-top: 0;">⏰ Important Timings (IST)</h3>
                        <p style="margin: 8px 0;"><strong>🏠 Leave Home By:</strong> {leave_time.strftime('%I:%M %p')}</p>
                        <p style="margin: 8px 0;"><strong>🏥 Reach Counter By:</strong> {reach_time.strftime('%I:%M %p')}</p>
                        <p style="margin: 8px 0;"><strong>📅 Date:</strong> {reach_time.strftime('%d %B %Y')}</p>
                        <p style="margin: 8px 0;"><strong>🚗 Travel Time:</strong> ~{int((reach_time - leave_time).total_seconds() / 60)} mins</p>
                      </div>

                      <p style="color: #666; font-size: 14px;">💡 <em>Tip: Leave 10 minutes before your estimated time to avoid delays.</em></p>

                      <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">
                      <p style="color: #999; font-size: 12px;">QueueFlow - Smart Queue Management Platform</p>
                    </div>
                  </body>
                </html>
                """
            },
            timeout=10
        )
        if response.status_code == 201:
            print(f"✅ Timing alert sent to {email}")
            return True
        else:
            print(f"❌ Brevo error: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Email error: {e}")
        return False
