from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from models import User, ServiceCenter, Admin, Token
from extensions import db
from auth import admin_required
from utils import (get_ist_now, get_ist_now_aware, utc_to_ist,
                   get_serving_token, get_walkin_serving_token,
                   get_walkin_queue_count, expire_old_tokens,
                   recalculate_queue_times, send_reset_email)
import secrets
import pytz

IST = pytz.timezone('Asia/Kolkata')

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


@admin_bp.route('/dashboard')
@admin_required
def admin_dashboard():
    
    # Auto-expire late tokens before loading dashboard
    expire_old_tokens()
    
    try:
        center_id = session['admin_center_id']
        center = ServiceCenter.query.get(center_id)
        current_time = get_ist_now_aware()  # Use timezone-aware IST for comparisons
        
        # Currently Serving Token
        serving_token = get_serving_token(center_id)
        
        # Get all active tokens
        waiting_tokens = []
        try:
            waiting_tokens = Token.query.filter_by(
                service_center_id=center_id, 
                status='Active',
                is_walkin=False
            ).order_by(Token.id).all()
        except Exception as e:
            print(f"⚠️ is_walkin column error: {e}")
            waiting_tokens = Token.query.filter_by(
                service_center_id=center_id, 
                status='Active'
            ).order_by(Token.id).all()
        
        # Find next eligible token - can call at arrival time
        next_eligible_token = None
        can_call_next = False
        
        if not serving_token:
            # Counter is free, find first arrived token
            for token in waiting_tokens:
                if token.reach_time:
                    reach_time = utc_to_ist(token.reach_time)
                    # Can call at arrival time (no buffer blocking)
                    if current_time >= reach_time:
                        next_eligible_token = token
                        can_call_next = True
                        break
                else:
                    # No reach_time, can call immediately
                    next_eligible_token = token
                    can_call_next = True
                    break
        
        # Enrich tokens with status badges
        enriched_tokens = []
        for token in waiting_tokens:
            try:
                token_data = {
                    'token': token,
                    'status_badge': 'Travelling',
                    'is_late': False
                }
                
                if token.reach_time:
                    reach_time = utc_to_ist(token.reach_time)
                    if current_time >= reach_time:
                        token_data['status_badge'] = 'Arrived'
                        # Late if > 5 min after arrival
                        if current_time > (reach_time + timedelta(minutes=5)):
                            token_data['status_badge'] = 'Late'
                            token_data['is_late'] = True
                
                enriched_tokens.append(token_data)
            except Exception as e:
                print(f"⚠️ Token enrichment error: {e}")
                continue
        
        # Walk-in Queue
        walkin_serving_token = get_walkin_serving_token(center_id)
        walkin_waiting_tokens = []
        try:
            walkin_waiting_tokens = Token.query.filter_by(
                service_center_id=center_id,
                status='Active',
                is_walkin=True
            ).order_by(Token.id).all()
        except:
            pass
        
        return render_template('admin/admin_dashboard.html', 
                             center=center,
                             serving_token=serving_token,
                             waiting_tokens=enriched_tokens,
                             next_eligible_token=next_eligible_token,
                             can_call_next=can_call_next,
                             walkin_serving_token=walkin_serving_token,
                             walkin_waiting_tokens=walkin_waiting_tokens,
                             current_time=current_time,
                             datetime=datetime)
    except Exception as e:
        import traceback
        print(f"❌ Admin dashboard error: {e}")
        print(traceback.format_exc())
        flash(f'Error loading dashboard: {str(e)}', 'danger')
        return redirect(url_for('admin.admin_login'))


@admin_bp.route('/queue-state')
def admin_queue_state():
    """Real-time queue state API for auto-refresh"""
    if 'admin_id' not in session:
        return {'error': 'Unauthorized'}, 401
    
    try:
        center_id = session['admin_center_id']
        current_time = get_ist_now()
        
        serving_token = get_serving_token(center_id)
        waiting_tokens = Token.query.filter_by(
            service_center_id=center_id,
            status='Active',
            is_walkin=False
        ).order_by(Token.estimated_service_start).all()
        
        # Build response
        response = {
            'current_time': current_time.isoformat(),
            'serving': None,
            'next_eligible': None,
            'can_call_next': False,
            'queue': []
        }
        
        # Serving token data
        if serving_token:
            try:
                service_end = utc_to_ist(serving_token.actual_service_end)
                if service_end:
                    remaining_seconds = int((service_end - current_time).total_seconds())
                else:
                    remaining_seconds = 0
                
                response['serving'] = {
                    'token_number': serving_token.token_number,
                    'user_name': serving_token.user.name if serving_token.user else 'Unknown',
                    'remaining_seconds': max(0, remaining_seconds)
                }
            except Exception as e:
                print(f"❌ Error processing serving token: {e}")
        
        # Check if can call next - at arrival time, not after buffer
        if not serving_token or (serving_token.actual_service_end and serving_token.actual_service_end <= current_time):
            for token in waiting_tokens:
                try:
                    if token.reach_time:
                        reach_time = utc_to_ist(token.reach_time)
                        # Can call at arrival time (no buffer blocking)
                        if current_time >= reach_time:
                            response['can_call_next'] = True
                            response['next_eligible'] = {
                                'token_number': token.token_number,
                                'user_name': token.user.name if token.user else 'Unknown'
                            }
                            break
                    else:
                        # No reach_time, can call immediately
                        response['can_call_next'] = True
                        response['next_eligible'] = {
                            'token_number': token.token_number,
                            'user_name': token.user.name if token.user else 'Unknown'
                        }
                        break
                except Exception as e:
                    print(f"❌ Error checking token eligibility: {e}")
                    continue
        
        # Queue list
        for token in waiting_tokens:
            try:
                reach_time = utc_to_ist(token.reach_time)
                if reach_time:
                    arrival_seconds = int((reach_time - current_time).total_seconds())
                    status = 'Travelling'
                    
                    if current_time >= reach_time:
                        status = 'Arrived'
                        # Late if > 5 min after arrival
                        if current_time > (reach_time + timedelta(minutes=5)):
                            status = 'Late'
                    
                    response['queue'].append({
                        'token_number': token.token_number,
                        'user_name': token.user.name if token.user else 'Unknown',
                        'arrival_seconds': arrival_seconds,
                        'status': status
                    })
            except Exception as e:
                print(f"❌ Error processing queue token: {e}")
                continue
        
        return response
    except Exception as e:
        print(f"❌ Error in admin_queue_state: {e}")
        return {'error': 'Internal server error'}, 500


@admin_bp.route('/call_next')
def call_next():
    if 'admin_id' not in session:
        return redirect(url_for('admin.admin_login'))
    
    # Auto-expire late tokens before calling next
    expire_old_tokens()
    
    center_id = session['admin_center_id']
    current_time = get_ist_now()  # UTC for DB
    current_time_aware = get_ist_now_aware()  # IST aware for comparisons
    
    try:
        serving_token = get_serving_token(center_id)
    except:
        serving_token = None
    
    if serving_token:
        serving_token.status = 'Completed'
        serving_token.completed_time = current_time
    
    try:
        next_token = Token.query.filter_by(
            service_center_id=center_id,
            status='Active',
            is_walkin=False
        ).order_by(Token.id).first()
    except:
        next_token = None
    
    if next_token:
        # Check if token has arrived (at arrival time, not after buffer)
        if next_token.reach_time:
            reach_time = utc_to_ist(next_token.reach_time)
            if current_time_aware < reach_time:
                db.session.commit()
                flash(f'Token {next_token.token_number} has not arrived yet. Expected at {reach_time.strftime("%I:%M %p")}', 'warning')
                return redirect(url_for('admin.admin_dashboard'))
            
            # Auto-skip if > 15 min late
            if current_time_aware > (reach_time + timedelta(minutes=15)):
                next_token.status = 'Expired'
                next_token.no_show_reason = 'Auto-skipped: More than 15 minutes late'
                next_token.no_show_time = current_time
                db.session.commit()
                flash(f'Token {next_token.token_number} auto-skipped (>15 min late). Calling next token...', 'warning')
                return redirect(url_for('admin.call_next'))
        
        next_token.status = 'Serving'
        next_token.actual_service_start = current_time
        next_token.actual_service_end = current_time + timedelta(minutes=ServiceCenter.query.get(center_id).avg_service_time)
        db.session.commit()
        flash(f'Token {next_token.token_number} is now being served.', 'success')
    else:
        db.session.commit()
        flash('No tokens in queue.', 'info')
    
    return redirect(url_for('admin.admin_dashboard'))


@admin_bp.route('/call_next_walkin')
def call_next_walkin():
    if 'admin_id' not in session:
        return redirect(url_for('admin.admin_login'))
    
    center_id = session['admin_center_id']
    
    try:
        walkin_serving_token = get_walkin_serving_token(center_id)
    except:
        walkin_serving_token = None
    
    if walkin_serving_token:
        walkin_serving_token.status = 'Completed'
        walkin_serving_token.completed_time = get_ist_now()
    
    try:
        next_token = Token.query.filter_by(
            service_center_id=center_id,
            status='Active',
            is_walkin=True
        ).order_by(Token.id).first()
    except:
        next_token = None
    
    if next_token:
        next_token.status = 'Serving'
        db.session.commit()
        flash(f'Walk-in token {next_token.token_number} is now being served.', 'success')
    else:
        db.session.commit()
        flash('No walk-in tokens in queue.', 'info')
    
    return redirect(url_for('admin.admin_dashboard'))


@admin_bp.route('/complete/<int:token_id>')
def complete_token(token_id):
    if 'admin_id' not in session:
        return redirect(url_for('admin.admin_login'))
    
    token = Token.query.get_or_404(token_id)
    token.status = 'Completed'
    token.completed_time = get_ist_now()
    db.session.commit()
    flash('Token marked as completed.', 'success')
    return redirect(url_for('admin.admin_dashboard'))


@admin_bp.route('/no_show/<int:token_id>', methods=['GET', 'POST'])
def no_show(token_id):
    if 'admin_id' not in session:
        return redirect(url_for('admin.admin_login'))
    
    token = Token.query.get_or_404(token_id)
    
    if request.method == 'POST':
        reason = request.form.get('reason', '').strip()
        notes = request.form.get('notes', '').strip()
        
        if not reason:
            flash('Please provide a reason for marking as no-show.', 'danger')
            return redirect(url_for('admin.admin_dashboard'))
        
        full_reason = reason
        if notes:
            full_reason += f" - {notes}"
        
        center_id = token.service_center_id
        token.status = 'Expired'
        token.no_show_reason = full_reason
        token.no_show_time = get_ist_now()
        
        user = User.query.get(token.user_id)
        user.no_show_count += 1
        
        db.session.commit()
        
        # Recalculate queue times for remaining tokens
        recalculate_queue_times(center_id)
        
        flash('Token marked as no-show with reason recorded.', 'warning')
        return redirect(url_for('admin.admin_dashboard'))
    
    return render_template('admin/no_show_form.html', token=token)


@admin_bp.route('/add_walkin', methods=['GET', 'POST'])
def add_walkin():
    if 'admin_id' not in session:
        return redirect(url_for('admin.admin_login'))
    
    center_id = session.get('admin_center_id')
    if not center_id:
        flash('Session expired. Please login again.', 'danger')
        return redirect(url_for('admin.admin_login'))
    
    center = ServiceCenter.query.get(center_id)
    if not center:
        flash('Service center not found.', 'danger')
        return redirect(url_for('admin.admin_login'))
    
    if request.method == 'POST':
        try:
            name = request.form.get('name', 'Walk-in Customer').strip()
            mobile = request.form.get('mobile', '').strip()
            
            try:
                if get_walkin_queue_count(center_id) >= 15:
                    flash('Walk-in queue is full!', 'warning')
                    return redirect(url_for('admin.admin_dashboard'))
            except:
                pass
            
            # Create or get user
            if mobile and len(mobile) == 10:
                user = User.query.filter_by(mobile=mobile).first()
                if not user:
                    user = User(name=name, mobile=mobile, password=generate_password_hash('walkin123'))
                    db.session.add(user)
                    db.session.flush()
            else:
                # Anonymous walk-in
                timestamp = int(get_ist_now().timestamp())
                user = User(name=name, mobile=f'W{timestamp}', email=f'walkin{timestamp}@queueflow.com', password=generate_password_hash('walkin123'))
                db.session.add(user)
                db.session.flush()
            
            # Generate token with W prefix
            today = get_ist_now().date()
            count = Token.query.filter(
                Token.service_center_id == center_id,
                db.func.date(Token.created_time) == today
            ).count()
            token_number = f"W{count + 1:03d}"
            
            token = Token(
                user_id=user.id,
                service_center_id=center_id,
                token_number=token_number,
                status='Active',
                created_time=get_ist_now(),
                is_walkin=True
            )
            db.session.add(token)
            db.session.commit()
            
            flash(f'Walk-in token {token_number} created successfully!', 'success')
            return redirect(url_for('admin.token_qr', token_number=token_number))
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error creating walk-in token: {e}")
            import traceback
            traceback.print_exc()
            flash(f'Error creating walk-in token: {str(e)}', 'danger')
            return redirect(url_for('admin.admin_dashboard'))
    
    return render_template('admin/add_walkin.html', center=center)


@admin_bp.route('/history')
def admin_history():
    if 'admin_id' not in session:
        return redirect(url_for('admin.admin_login'))
    
    center_id = session['admin_center_id']
    center = ServiceCenter.query.get(center_id)
    
    try:
        tokens = Token.query.filter_by(service_center_id=center_id).filter(
            Token.status.in_(['Completed', 'Expired'])
        ).order_by(Token.created_time.desc()).limit(100).all()
    except Exception as e:
        print(f"❌ Error fetching history: {e}")
        tokens = []
    
    return render_template('admin/admin_history.html', center=center, tokens=tokens, IST=IST, datetime=datetime)


@admin_bp.route('/analytics')
def admin_analytics():
    """Admin analytics page - Chart.js powered"""
    if 'admin_id' not in session:
        return redirect(url_for('admin.admin_login'))
    
    center_id = session['admin_center_id']
    center = ServiceCenter.query.get(center_id)
    
    if not center:
        flash('Service center not found', 'danger')
        return redirect(url_for('admin.admin_dashboard'))
    
    return render_template('admin/admin_analytics.html', center=center)


@admin_bp.route('/api/analytics')
def api_admin_analytics():
    """JSON endpoint for admin analytics data"""
    if 'admin_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    center_id = session['admin_center_id']
    today = datetime.now().date()
    
    # Daily customers
    daily_customers = Token.query.filter(
        Token.service_center_id == center_id,
        db.func.date(Token.created_time) == today
    ).count()
    
    # Last 7 days trend — single GROUP BY query instead of 7 separate count queries
    seven_days_ago = today - timedelta(days=6)
    trend_rows = db.session.query(
        db.func.date(Token.created_time).label('day'),
        db.func.count(Token.id).label('cnt')
    ).filter(
        Token.service_center_id == center_id,
        db.func.date(Token.created_time) >= seven_days_ago
    ).group_by('day').all()
    trend_map = {str(row.day): row.cnt for row in trend_rows}
    trend_data = []
    for i in range(6, -1, -1):
        date = today - timedelta(days=i)
        trend_data.append({'date': date.strftime('%a'), 'count': trend_map.get(str(date), 0)})
    
    # Online vs Walk-in
    total_tokens = Token.query.filter_by(service_center_id=center_id).count()
    walkin_tokens = Token.query.filter_by(service_center_id=center_id, is_walkin=True).count()
    online_tokens = total_tokens - walkin_tokens
    
    # Status breakdown
    completed = Token.query.filter_by(service_center_id=center_id, status='Completed').count()
    no_show = Token.query.filter_by(service_center_id=center_id, status='No Show').count()
    expired = Token.query.filter_by(service_center_id=center_id, status='Expired').count()
    
    # Peak hours — use SQL GROUP BY instead of fetching all tokens into Python
    peak_hours_query = db.session.query(
        db.func.strftime('%H', Token.created_time).label('hour'),
        db.func.count(Token.id).label('cnt')
    ).filter_by(service_center_id=center_id).group_by('hour').order_by(db.desc('cnt')).limit(5).all()
    peak_hours = [(int(h), c) for h, c in peak_hours_query if h is not None]
    
    return jsonify({
        'daily_customers': daily_customers,
        'total_tokens': total_tokens,
        'trend': trend_data,
        'booking_types': {
            'online': online_tokens,
            'walkin': walkin_tokens
        },
        'status': {
            'completed': completed,
            'no_show': no_show,
            'expired': expired
        },
        'peak_hours': [{'hour': h, 'count': c} for h, c in peak_hours]
    })


@admin_bp.route('/generate-demo-data')
def generate_demo_data():
    """Generate demo tokens for analytics testing"""
    if 'admin_id' not in session:
        return redirect(url_for('admin.admin_login'))
    
    try:
        center_id = session['admin_center_id']
        center = ServiceCenter.query.get(center_id)
        
        # Get or create demo user
        demo_user = User.query.filter_by(mobile='0000000000').first()
        if not demo_user:
            demo_user = User(name='Demo User', mobile='0000000000', email='demo@queueflow.com', password=generate_password_hash('demo123'))
            db.session.add(demo_user)
            db.session.commit()
        
        # Generate tokens for last 7 days
        count = 0
        for days_ago in range(7):
            date = datetime.now() - timedelta(days=days_ago)
            tokens_per_day = 5 + (days_ago % 3) * 2  # 5-9 tokens per day
            
            for i in range(tokens_per_day):
                # Random time during business hours
                hour = 9 + (i * 2) % 9  # 9 AM to 5 PM
                token_time = date.replace(hour=hour, minute=i*10 % 60, second=0, microsecond=0)
                
                token = Token(
                    user_id=demo_user.id,
                    service_center_id=center_id,
                    token_number=f"D{count+1:03d}",
                    status='Completed',
                    created_time=token_time,
                    completed_time=token_time + timedelta(minutes=center.avg_service_time),
                    is_walkin=(i % 3 == 0)  # Every 3rd token is walk-in
                )
                db.session.add(token)
                count += 1
        
        db.session.commit()
        flash(f'✅ Generated {count} demo tokens for analytics!', 'success')
        return redirect(url_for('admin.admin_analytics'))
    except Exception as e:
        flash(f'Error generating demo data: {str(e)}', 'danger')
        return redirect(url_for('admin.admin_dashboard'))


@admin_bp.route('/profile', methods=['GET', 'POST'])
def admin_profile():
    if 'admin_id' not in session:
        return redirect(url_for('admin.admin_login'))
    
    center_id = session['admin_center_id']
    center = ServiceCenter.query.get(center_id)
    admin = Admin.query.get(session['admin_id'])
    
    if request.method == 'POST':
        try:
            center.description = request.form.get('description', '').strip()
            center.phone = request.form.get('phone', '').strip()
            center.email = request.form.get('email', '').strip()
            center.website = request.form.get('website', '').strip()
            center.business_hours = request.form.get('business_hours', '').strip()
            center.services_offered = request.form.get('services_offered', '').strip()
            center.facilities = request.form.get('facilities', '').strip()
            center.avg_service_time = int(request.form.get('avg_service_time', 15))
            
            # Update location
            center.location = request.form.get('location', '').strip()
            lat = request.form.get('latitude', '').strip()
            lon = request.form.get('longitude', '').strip()
            if lat and lon:
                center.latitude = float(lat)
                center.longitude = float(lon)
            
            # Update admin email
            admin.email = request.form.get('admin_email', '').strip()
            
            db.session.commit()
            flash('Profile updated successfully!', 'success')
            return redirect(url_for('admin.admin_profile'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating profile: {str(e)}', 'danger')
    
    return render_template('admin/admin_profile.html', center=center, admin=admin)


@admin_bp.route('/update-all-coordinates')
def update_all_coordinates():
    """Update coordinates for all demo service centers"""
    coordinates = {
        'APOLLO CLINIC': (21.1458, 79.0882),
        'The Nagpur Clinic': (21.1466, 79.0882),
        'Nagpur Clinic': (21.1498, 79.0806),
        'MOTHER INDIA FETAL MEDICINE CENTRE': (21.1307, 79.0711),
        'Ashvatam Clinic': (21.1509, 79.0831),
        'Apna Clinic': (21.1540, 79.0849),
        'Dr.Agrawal Multispeciality Clinic': (21.1180, 79.0510),
        'Shree Clinic': (21.1220, 79.0420),
        'Sai Clinic': (21.1650, 79.0900),
        'Suyash Clinic': (21.1700, 79.0950),
        'INC CLINIC NAGPUR': (21.1350, 79.0750),
        'Apple Service - NGRT Systems': (21.1458, 79.0882),
        'Samsung Service - The Mobile Magic': (21.1498, 79.0806),
        'Samsung Service - Spectrum Marketing': (21.1466, 79.0882),
        'Samsung Service - Karuna Management': (21.1400, 79.0700),
        'Samsung CE - Akshay Refrigeration': (21.1600, 79.1000),
        'vivo India Service Center': (21.1509, 79.0831),
        'vivo & iQOO Service Center': (21.1520, 79.0840),
        'OPPO Service Center': (21.1498, 79.0806),
    }
    
    results = ["<h2>📍 Coordinate Update Results</h2>"]
    updated = 0
    
    for name, (lat, lng) in coordinates.items():
        center = ServiceCenter.query.filter_by(name=name).first()
        if center:
            center.latitude = lat
            center.longitude = lng
            updated += 1
            results.append(f"<p>✅ Updated: {name} → ({lat}, {lng})</p>")
        else:
            results.append(f"<p>⚠️ Not found: {name}</p>")
    
    db.session.commit()
    results.append(f"<hr><h3>🎉 Successfully updated {updated} service centers!</h3>")
    results.append("<p><a href='/services'>View Services</a> | <a href='/admin/dashboard'>Admin Dashboard</a></p>")
    
    return "".join(results)


@admin_bp.route('/migrate-db-add-column')
def migrate_db():
    """Manual migration endpoint to add missing columns"""
    results = []
    try:
        with db.engine.connect() as conn:
            # Fix mobile column length for walk-in users
            try:
                conn.execute(db.text("ALTER TABLE users ALTER COLUMN mobile TYPE VARCHAR(20)"))
                conn.commit()
                results.append("✅ Updated mobile column to VARCHAR(20)")
            except Exception as e:
                results.append(f"⚠️ mobile column: {str(e)}")
            
            # Add new service center columns
            service_center_columns = [
                ('description', 'VARCHAR(500)'),
                ('phone', 'VARCHAR(15)'),
                ('email', 'VARCHAR(100)'),
                ('website', 'VARCHAR(100)'),
                ('business_hours', 'VARCHAR(100)'),
                ('services_offered', 'VARCHAR(500)'),
                ('facilities', 'VARCHAR(500)')
            ]
            
            for col_name, col_type in service_center_columns:
                try:
                    result = conn.execute(db.text(
                        f"SELECT column_name FROM information_schema.columns "
                        f"WHERE table_name='service_centers' AND column_name='{col_name}'"
                    ))
                    if not result.fetchone():
                        conn.execute(db.text(
                            f"ALTER TABLE service_centers ADD COLUMN {col_name} {col_type}"
                        ))
                        conn.commit()
                        results.append(f"✅ Added {col_name} column to service_centers")
                    else:
                        results.append(f"ℹ️ {col_name} column already exists")
                except Exception as e:
                    results.append(f"⚠️ {col_name}: {str(e)}")
            
            # Add new token columns for fixed times
            token_columns = [
                ('leave_time', 'TIMESTAMP'),
                ('reach_time', 'TIMESTAMP'),
                ('estimated_service_start', 'TIMESTAMP'),
                ('estimated_service_end', 'TIMESTAMP'),
                ('actual_service_start', 'TIMESTAMP'),
                ('actual_service_end', 'TIMESTAMP'),
                ('completed_time', 'TIMESTAMP'),
                ('no_show_reason', 'VARCHAR(500)'),
                ('no_show_time', 'TIMESTAMP'),
                ('is_walkin', 'BOOLEAN DEFAULT FALSE')
            ]
            
            for col_name, col_type in token_columns:
                try:
                    result = conn.execute(db.text(
                        f"SELECT column_name FROM information_schema.columns "
                        f"WHERE table_name='tokens' AND column_name='{col_name}'"
                    ))
                    if not result.fetchone():
                        conn.execute(db.text(
                            f"ALTER TABLE tokens ADD COLUMN {col_name} {col_type}"
                        ))
                        conn.commit()
                        results.append(f"✅ Added {col_name} column to tokens")
                    else:
                        results.append(f"ℹ️ {col_name} column already exists")
                except Exception as e:
                    results.append(f"⚠️ {col_name}: {str(e)}")
            
            return "<h2>Migration Results</h2>" + "".join([f"<p>{r}</p>" for r in results])
    except Exception as e:
        return f"<h2>Migration Error</h2><p>❌ {str(e)}</p>"


@admin_bp.route('/debug/verify-timing-system')
def debug_verify_timing():
    """Debug endpoint to verify timing system works for all service centers"""
    results = []
    results.append("<h2>🔍 Timing System Verification</h2>")
    
    # Check all service centers
    centers = ServiceCenter.query.all()
    results.append(f"<p><strong>Total Service Centers:</strong> {len(centers)}</p>")
    
    for center in centers:
        results.append(f"<hr><h3>{center.name} (ID: {center.id})</h3>")
        results.append(f"<p><strong>Category:</strong> {center.category}</p>")
        results.append(f"<p><strong>Location:</strong> {center.location}</p>")
        results.append(f"<p><strong>Avg Service Time:</strong> {center.avg_service_time} mins</p>")
        
        # Check recent tokens
        recent_tokens = Token.query.filter_by(service_center_id=center.id).order_by(Token.created_time.desc()).limit(5).all()
        results.append(f"<p><strong>Recent Tokens:</strong> {len(recent_tokens)}</p>")
        
        if recent_tokens:
            results.append("<table border='1' style='border-collapse: collapse; margin: 10px 0;'>")
            results.append("<tr><th>Token</th><th>Status</th><th>Leave Time</th><th>Reach Time</th><th>Email Sent</th></tr>")
            for token in recent_tokens:
                leave_str = token.leave_time.strftime('%Y-%m-%d %H:%M') if token.leave_time else 'N/A'
                reach_str = token.reach_time.strftime('%Y-%m-%d %H:%M') if token.reach_time else 'N/A'
                has_times = '✅' if (token.leave_time and token.reach_time) else '❌'
                results.append(f"<tr><td>{token.token_number}</td><td>{token.status}</td><td>{leave_str}</td><td>{reach_str}</td><td>{has_times}</td></tr>")
            results.append("</table>")
        else:
            results.append("<p><em>No tokens yet</em></p>")
    
    results.append("<hr><h3>✅ System Status</h3>")
    results.append("<p>The timing calculation system is <strong>active for ALL service centers</strong>.</p>")
    results.append("<p>If times are missing, it means:</p>")
    results.append("<ul>")
    results.append("<li>Token was created before timing system was implemented</li>")
    results.append("<li>Token is still in 'PendingPayment' status (times calculated after payment)</li>")
    results.append("<li>Token was created via walk-in (different flow)</li>")
    results.append("</ul>")
    
    return "".join(results)


@admin_bp.route('/forgot-password', methods=['GET', 'POST'])
def admin_forgot_password():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        
        admin = Admin.query.filter_by(username=username).first()
        if admin and admin.email == email:
            # Generate reset token
            reset_token = secrets.token_urlsafe(32)
            admin.reset_token = reset_token
            admin.reset_token_expiry = get_ist_now() + timedelta(hours=1)
            db.session.commit()
            
            # Send email
            reset_link = url_for('admin.admin_reset_password', token=reset_token, _external=True)
            if send_reset_email(email, reset_link, "Admin"):
                flash('Password reset link sent to your email!', 'success')
            else:
                flash('Email not configured. Contact super admin.', 'warning')
            return redirect(url_for('admin.admin_login'))
        else:
            flash('Invalid username or email!', 'danger')
    
    return render_template('admin/admin_forgot_password.html')


@admin_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def admin_reset_password(token):
    admin = Admin.query.filter_by(reset_token=token).first()
    
    if not admin or not admin.reset_token_expiry or admin.reset_token_expiry < get_ist_now():
        flash('Invalid or expired reset link!', 'danger')
        return redirect(url_for('admin.admin_login'))
    
    if request.method == 'POST':
        new_password = request.form.get('password')
        admin.password = generate_password_hash(new_password)
        admin.reset_token = None
        admin.reset_token_expiry = None
        db.session.commit()
        
        flash('Password reset successful! Please login.', 'success')
        return redirect(url_for('admin.admin_login'))
    
    return render_template('admin/admin_reset_password.html', token=token)


@admin_bp.route('/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        admin = Admin.query.filter_by(username=username).first()
        if admin and check_password_hash(admin.password, password):
            session['admin_id'] = admin.id
            session['admin_center_id'] = admin.service_center_id
            return redirect(url_for('admin.admin_dashboard'))
        
        flash('Invalid credentials!', 'danger')
    
    return render_template('admin/admin_login.html')


@admin_bp.route('/logout')
def admin_logout():
    session.clear()
    return redirect(url_for('admin.admin_login'))


@admin_bp.route('/delete-center', methods=['POST'])
def admin_delete_center():
    if 'admin_id' not in session:
        return redirect(url_for('admin.admin_login'))
    
    center_id = session['admin_center_id']
    center = ServiceCenter.query.get_or_404(center_id)
    center_name = center.name
    
    # Delete all tokens for this center
    Token.query.filter_by(service_center_id=center_id).delete()
    
    # Delete admin account
    Admin.query.filter_by(service_center_id=center_id).delete()
    
    # Delete the service center
    db.session.delete(center)
    db.session.commit()
    
    # Logout admin
    session.clear()
    
    flash(f'Your service center "{center_name}" has been deleted successfully.', 'info')
    return redirect(url_for('main.index'))


@admin_bp.route('/token-qr/<token_number>')
def token_qr(token_number):
    """Generate QR code for token tracking"""
    import qrcode
    import io
    import base64
    token = Token.query.filter_by(token_number=token_number).first_or_404()

    # Generate tracking URL
    track_url = url_for('user.track_status', token_number=token_number, _external=True)

    # Generate QR code
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(track_url)
    qr.make(fit=True)

    img = qr.make_image(fill_color="#0F172A", back_color="white")

    # Convert to base64
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    img_base64 = base64.b64encode(buffer.getvalue()).decode()

    return render_template('user/token_qr.html',
                           token=token,
                           qr_code=img_base64,
                           track_url=track_url,
                           IST=IST)
