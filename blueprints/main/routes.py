from flask import render_template
from blueprints.main import main_bp
from extensions import db
from models import Token, ServiceCenter, User
from werkzeug.security import generate_password_hash
from datetime import datetime, timedelta
import random


@main_bp.route('/')
def index():
    try:
        return render_template('main/home.html')
    except Exception as e:
        print(f"❌ Landing page error: {e}")
        import traceback
        traceback.print_exc()
        return f"<h1>Error loading page</h1><pre>{str(e)}</pre>", 500


@main_bp.route('/pricing')
def pricing():
    return render_template('main/pricing.html')


@main_bp.route('/terms')
def terms():
    return render_template('main/terms.html')


@main_bp.route('/privacy')
def privacy():
    return render_template('main/privacy.html')


@main_bp.route('/seed-demo-data')
def seed_demo_data():
    """Seed all service centers with 30-day analytics history + live demo queue. Run once on fresh DB."""
    try:
        DEMO_USERS_DATA = [
            ('Rahul Sharma',   '9876543210', 'rahul@demo.com'),
            ('Priya Patel',    '9876543211', 'priya@demo.com'),
            ('Amit Kumar',     '9876543212', 'amit@demo.com'),
            ('Sneha Deshmukh', '9876543213', 'sneha@demo.com'),
            ('Vikram Singh',   '9876543214', 'vikram@demo.com'),
            ('Neha Joshi',     '9876543215', 'neha@demo.com'),
            ('Rohan Mehta',    '9876543216', 'rohan@demo.com'),
            ('Anjali Rao',     '9876543217', 'anjali@demo.com'),
            ('Suresh Patil',   '9876543218', 'suresh@demo.com'),
            ('Kavita Sharma',  '9876543219', 'kavita@demo.com'),
        ]

        # Ensure demo users exist
        users = []
        for name, mobile, email in DEMO_USERS_DATA:
            u = User.query.filter_by(mobile=mobile).first()
            if not u:
                u = User(name=name, mobile=mobile, email=email,
                         password=generate_password_hash('demo123'),
                         latitude=21.1458, longitude=79.0882)
                db.session.add(u)
            users.append(u)
        db.session.commit()

        centers = ServiceCenter.query.order_by(ServiceCenter.id).all()
        if not centers:
            return "<h2>❌ No service centers found. Deploy the app first.</h2>"

        now = datetime.utcnow()
        today = now.date()
        statuses_pool = ['Completed'] * 7 + ['No-Show'] * 2 + ['Expired'] * 1
        total_history = 0
        total_queue = 0

        for center in centers:
            avg = center.avg_service_time or 20

            # Clear existing demo tokens for this center
            Token.query.filter(
                Token.service_center_id == center.id,
                Token.token_number.like('H%')
            ).delete(synchronize_session=False)
            # Clear today's tokens using Python-side date comparison
            cutoff = now.replace(hour=0, minute=0, second=0, microsecond=0)
            Token.query.filter(
                Token.service_center_id == center.id,
                Token.created_time >= cutoff
            ).delete(synchronize_session=False)
            db.session.commit()

            # 30 days of historical tokens
            history = []
            for days_ago in range(1, 31):
                day_base = (now - timedelta(days=days_ago)).replace(
                    hour=3, minute=30, second=0, microsecond=0)
                daily_count = random.randint(8, 18)
                for i in range(daily_count):
                    offset = int(i * (8 * 60) / daily_count)
                    t_time = day_base + timedelta(minutes=offset)
                    status = random.choice(statuses_pool)
                    user = random.choice(users)
                    history.append(Token(
                        user_id=user.id,
                        service_center_id=center.id,
                        token_number=f'H{days_ago:02d}{i:02d}',
                        status=status,
                        created_time=t_time,
                        completed_time=t_time + timedelta(minutes=avg) if status == 'Completed' else None,
                        actual_service_start=t_time if status == 'Completed' else None,
                        actual_service_end=t_time + timedelta(minutes=avg) if status == 'Completed' else None,
                        estimated_service_start=t_time,
                        estimated_service_end=t_time + timedelta(minutes=avg),
                        leave_time=t_time - timedelta(minutes=20),
                        reach_time=t_time,
                        is_walkin=(i % 4 == 0),
                        no_show_reason='Did not arrive' if status == 'No-Show' else None,
                    ))
            db.session.add_all(history)
            db.session.commit()
            total_history += len(history)

            # Today's live demo queue
            base_time = now.replace(hour=3, minute=30, second=0, microsecond=0)
            serve_start = now - timedelta(minutes=5)
            queue = []

            for i in range(4):  # 4 Completed
                start = now - timedelta(minutes=120 - i * 25)
                end = start + timedelta(minutes=avg)
                queue.append(Token(
                    user_id=users[i].id, service_center_id=center.id,
                    token_number=f'T{i+1:03d}', status='Completed',
                    created_time=base_time,
                    actual_service_start=start, actual_service_end=end, completed_time=end,
                    estimated_service_start=start, estimated_service_end=end,
                    leave_time=start - timedelta(minutes=15), reach_time=start, is_walkin=False,
                ))

            queue.append(Token(  # 1 Online Serving
                user_id=users[4].id, service_center_id=center.id,
                token_number='T005', status='Serving', created_time=base_time,
                actual_service_start=serve_start,
                estimated_service_start=serve_start,
                estimated_service_end=serve_start + timedelta(minutes=avg),
                leave_time=serve_start - timedelta(minutes=15), reach_time=serve_start, is_walkin=False,
            ))

            for i in range(5):  # 5 Active online
                est_start = serve_start + timedelta(minutes=(i + 1) * avg)
                queue.append(Token(
                    user_id=users[5 + i].id, service_center_id=center.id,
                    token_number=f'T{6+i:03d}', status='Active',
                    created_time=now - timedelta(minutes=30 - i * 4),
                    estimated_service_start=est_start,
                    estimated_service_end=est_start + timedelta(minutes=avg),
                    leave_time=est_start - timedelta(minutes=20), reach_time=est_start, is_walkin=False,
                ))

            wi_start = now - timedelta(minutes=8)
            queue.append(Token(  # 1 Walk-in Serving
                user_id=users[2].id, service_center_id=center.id,
                token_number='W000', status='Serving', created_time=base_time,
                actual_service_start=wi_start,
                estimated_service_start=wi_start,
                estimated_service_end=wi_start + timedelta(minutes=avg),
                is_walkin=True,
            ))

            for i in range(2):  # 2 Active walk-in
                est_start = now + timedelta(minutes=(i + 1) * avg)
                queue.append(Token(
                    user_id=users[i].id, service_center_id=center.id,
                    token_number=f'W{i+1:03d}', status='Active',
                    created_time=now - timedelta(minutes=10 - i * 3),
                    estimated_service_start=est_start,
                    estimated_service_end=est_start + timedelta(minutes=avg),
                    is_walkin=True,
                ))

            db.session.add_all(queue)
            db.session.commit()
            total_queue += len(queue)

        return (
            f"<h2>✅ Demo data seeded successfully!</h2>"
            f"<p>Centers: {len(centers)}</p>"
            f"<p>History tokens: {total_history}</p>"
            f"<p>Live queue tokens: {total_queue}</p>"
            f"<hr>"
            f"<p><a href='/admin/login'>Admin Login</a> — apollo@admin.com / admin123</p>"
            f"<p><a href='/superadmin/login'>Super Admin Login</a> — superadmin@queueflow.com / superadmin123</p>"
            f"<p><a href='/login'>User Login</a> — 9876543210 / demo123</p>"
        )
    except Exception as e:
        db.session.rollback()
        import traceback
        return f"<h2>❌ Error: {str(e)}</h2><pre>{traceback.format_exc()}</pre>"


@main_bp.route('/test-email-config')
def test_email_config():
    """Test endpoint to verify email configuration"""
    from flask import current_app
    config_status = {
        'MAIL_SERVER': current_app.config.get('MAIL_SERVER', 'NOT SET'),
        'MAIL_PORT': current_app.config.get('MAIL_PORT', 'NOT SET'),
        'MAIL_USERNAME': current_app.config.get('MAIL_USERNAME', 'NOT SET'),
        'MAIL_PASSWORD_LENGTH': len(current_app.config.get('MAIL_PASSWORD', '')),
        'MAIL_USE_TLS': current_app.config.get('MAIL_USE_TLS', 'NOT SET'),
    }
    return f"<pre>{config_status}</pre><br><p>Password configured: {bool(current_app.config.get('MAIL_PASSWORD'))}</p>"


@main_bp.route('/test-send-email')
def test_send_email():
    """Test endpoint to actually send an email"""
    import os
    from utils import send_reset_email
    brevo_key = os.getenv('BREVO_API_KEY', '')
    if not brevo_key:
        return f"<h2>Email Send Test</h2><p>❌ BREVO_API_KEY not configured in environment variables</p>"

    try:
        test_link = "https://digital-queue-management-system-1.onrender.com/"
        result = send_reset_email('teltumdesahil441@gmail.com', test_link, 'Test')
        return f"<h2>Email Send Test</h2><p>Result: {'SUCCESS ✅' if result else 'FAILED ❌'}</p><p>Check Render logs and your email inbox</p>"
    except Exception as e:
        return f"<h2>Email Send Test</h2><p>ERROR: {str(e)}</p><p>Check Render logs for full traceback</p>"


@main_bp.route('/test-ors-api')
def test_ors_api():
    """Test endpoint to verify OpenRouteService API with traffic adjustment"""
    import os
    from utils import calculate_travel_time, get_ist_now_aware, get_traffic_multiplier
    ors_key = os.getenv('OPENROUTESERVICE_API_KEY', '')
    if not ors_key:
        return f"<h2>ORS API Test</h2><p>❌ OPENROUTESERVICE_API_KEY not configured</p>"

    try:
        user_lat, user_lon = 21.110168, 79.087917
        center_lat, center_lon = 20.9125252, 79.1210646

        travel_time = calculate_travel_time(user_lat, user_lon, center_lat, center_lon)

        if travel_time:
            current_time = get_ist_now_aware()
            multiplier = get_traffic_multiplier()
            base_time = round(travel_time / multiplier)

            return f"""
            <h2>ORS API Test + Traffic Adjustment</h2>
            <p>✅ <strong>SUCCESS!</strong></p>
            <p><strong>Current Time:</strong> {current_time.strftime('%I:%M %p')} (Hour: {current_time.hour})</p>
            <p><strong>Base Time (ORS):</strong> ~{base_time} minutes</p>
            <p><strong>Traffic Multiplier:</strong> {multiplier}x</p>
            <p><strong>Adjusted Time:</strong> {travel_time} minutes</p>
            <hr>
            <p><strong>Traffic Periods:</strong></p>
            <ul>
                <li>Peak (9-11 AM, 4-8 PM): ×2.0</li>
                <li>Normal (11 AM-4 PM, 8-10 PM): ×1.8</li>
                <li>Night (10 PM-6 AM): ×1.5</li>
            </ul>
            """
        else:
            return f"<h2>ORS API Test</h2><p>❌ FAILED - Check logs</p>"
    except Exception as e:
        return f"<h2>ORS API Test</h2><p>❌ ERROR: {str(e)}</p>"
