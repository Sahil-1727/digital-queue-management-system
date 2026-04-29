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
    """Populate all service centers with 30-day history + live demo queue. Hit once on fresh DB."""
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
            return "<h2>❌ No service centers found.</h2>"

        now = datetime.utcnow()
        statuses_pool = ['Completed'] * 7 + ['No-Show'] * 2 + ['Expired'] * 1
        total_history = 0
        total_queue = 0

        for center in centers:
            avg = center.avg_service_time or 20
            cutoff = now.replace(hour=0, minute=0, second=0, microsecond=0)

            # Clear old demo tokens
            Token.query.filter(Token.service_center_id == center.id,
                               Token.token_number.like('H%')).delete(synchronize_session=False)
            Token.query.filter(Token.service_center_id == center.id,
                               Token.created_time >= cutoff).delete(synchronize_session=False)
            db.session.commit()

            # 30 days of history
            history = []
            for days_ago in range(1, 31):
                day_base = (now - timedelta(days=days_ago)).replace(hour=3, minute=30, second=0, microsecond=0)
                daily_count = random.randint(8, 18)
                for i in range(daily_count):
                    t_time = day_base + timedelta(minutes=int(i * 480 / daily_count))
                    status = random.choice(statuses_pool)
                    user = random.choice(users)
                    history.append(Token(
                        user_id=user.id, service_center_id=center.id,
                        token_number=f'H{days_ago:02d}{i:02d}', status=status,
                        created_time=t_time,
                        completed_time=t_time + timedelta(minutes=avg) if status == 'Completed' else None,
                        actual_service_start=t_time if status == 'Completed' else None,
                        actual_service_end=t_time + timedelta(minutes=avg) if status == 'Completed' else None,
                        estimated_service_start=t_time,
                        estimated_service_end=t_time + timedelta(minutes=avg),
                        leave_time=t_time - timedelta(minutes=20), reach_time=t_time,
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
            for i in range(4):
                start = now - timedelta(minutes=120 - i * 25)
                end = start + timedelta(minutes=avg)
                queue.append(Token(
                    user_id=users[i].id, service_center_id=center.id,
                    token_number=f'T{i+1:03d}', status='Completed', created_time=base_time,
                    actual_service_start=start, actual_service_end=end, completed_time=end,
                    estimated_service_start=start, estimated_service_end=end,
                    leave_time=start - timedelta(minutes=15), reach_time=start, is_walkin=False,
                ))
            queue.append(Token(
                user_id=users[4].id, service_center_id=center.id,
                token_number='T005', status='Serving', created_time=base_time,
                actual_service_start=serve_start, estimated_service_start=serve_start,
                estimated_service_end=serve_start + timedelta(minutes=avg),
                leave_time=serve_start - timedelta(minutes=15), reach_time=serve_start, is_walkin=False,
            ))
            for i in range(5):
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
            queue.append(Token(
                user_id=users[2].id, service_center_id=center.id,
                token_number='W000', status='Serving', created_time=base_time,
                actual_service_start=wi_start, estimated_service_start=wi_start,
                estimated_service_end=wi_start + timedelta(minutes=avg), is_walkin=True,
            ))
            for i in range(2):
                est_start = now + timedelta(minutes=(i + 1) * avg)
                queue.append(Token(
                    user_id=users[i].id, service_center_id=center.id,
                    token_number=f'W{i+1:03d}', status='Active',
                    created_time=now - timedelta(minutes=10 - i * 3),
                    estimated_service_start=est_start,
                    estimated_service_end=est_start + timedelta(minutes=avg), is_walkin=True,
                ))
            db.session.add_all(queue)
            db.session.commit()
            total_queue += len(queue)

        return (
            f"<h2>✅ Demo data seeded!</h2>"
            f"<p>Centers: {len(centers)} | History tokens: {total_history} | Queue tokens: {total_queue}</p>"
            f"<p><a href='/admin/login'>Admin Login</a> — apollo@admin.com / admin123</p>"
            f"<p><a href='/superadmin/login'>Super Admin</a> — superadmin@queueflow.com / superadmin123</p>"
            f"<p><a href='/login'>User Login</a> — 9876543210 / demo123</p>"
        )
    except Exception as e:
        db.session.rollback()
        import traceback
        return f"<h2>❌ Error: {str(e)}</h2><pre>{traceback.format_exc()}</pre>"
