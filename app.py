from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import os
import secrets
import smtplib
import socket
import requests
import qrcode
import io
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'fallback-secret-key')

# Fix DATABASE_URL for PostgreSQL (Render uses postgres:// but SQLAlchemy needs postgresql://)
database_url = os.getenv('DATABASE_URL', 'sqlite:///database.db')
if database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql://', 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Email configuration
app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 465))
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME', '')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD', '')
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True

# Debug email config (remove in production)
print(f"📧 Email Config: Server={app.config['MAIL_SERVER']}, Port={app.config['MAIL_PORT']}")
print(f"📧 Username configured: {bool(app.config['MAIL_USERNAME'])}")
print(f"📧 Password configured: {bool(app.config['MAIL_PASSWORD'])}")

db = SQLAlchemy(app)

# Initialize database on startup
try:
    with app.app_context():
        db.create_all()
except Exception as e:
    print(f"Database initialization will happen on first request: {e}")

# Models
class User(db.Model): 
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    mobile = db.Column(db.String(10), unique=True, nullable=False)
    email = db.Column(db.String(100), nullable=False)
    password = db.Column(db.String(200), nullable=False)
    address = db.Column(db.String(200), nullable=True)
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    no_show_count = db.Column(db.Integer, default=0)
    reset_token = db.Column(db.String(100), nullable=True)
    reset_token_expiry = db.Column(db.DateTime, nullable=True)
    tokens = db.relationship('Token', backref='user', lazy=True)

class ServiceCenter(db.Model):
    __tablename__ = 'service_centers'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    location = db.Column(db.String(100), nullable=False)
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    avg_service_time = db.Column(db.Integer, default=15)  # minutes per token
    tokens = db.relationship('Token', backref='service_center', lazy=True)
    admins = db.relationship('Admin', backref='service_center', lazy=True)

class Admin(db.Model):
    __tablename__ = 'admins'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(100), nullable=True)
    password = db.Column(db.String(200), nullable=False)
    reset_token = db.Column(db.String(100), nullable=True)
    reset_token_expiry = db.Column(db.DateTime, nullable=True)
    service_center_id = db.Column(db.Integer, db.ForeignKey('service_centers.id'), nullable=False)

class Token(db.Model):
    __tablename__ = 'tokens'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    service_center_id = db.Column(db.Integer, db.ForeignKey('service_centers.id'), nullable=False)
    token_number = db.Column(db.String(10), nullable=False)
    status = db.Column(db.String(20), default='PendingPayment')  # PendingPayment, Active, Serving, Completed, Expired
    created_time = db.Column(db.DateTime, default=datetime.now)
    completed_time = db.Column(db.DateTime, nullable=True)
    no_show_reason = db.Column(db.String(500), nullable=True)
    no_show_time = db.Column(db.DateTime, nullable=True)
    is_walkin = db.Column(db.Boolean, default=False)

class SuperAdmin(db.Model):
    __tablename__ = 'super_admins'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(100), nullable=True)

class ServiceCenterRegistration(db.Model):
    __tablename__ = 'service_center_registrations'
    id = db.Column(db.Integer, primary_key=True)
    center_name = db.Column(db.String(100), nullable=False)
    organization_type = db.Column(db.String(50), nullable=False)
    owner_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(10), nullable=False)
    password = db.Column(db.String(200), nullable=False)
    alternate_phone = db.Column(db.String(10), nullable=True)
    city = db.Column(db.String(50), nullable=False)
    state = db.Column(db.String(50), nullable=False)
    pincode = db.Column(db.String(6), nullable=False)
    address = db.Column(db.String(200), nullable=False)
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    business_hours = db.Column(db.String(100), nullable=True)
    counters = db.Column(db.Integer, nullable=True)
    daily_customers = db.Column(db.Integer, nullable=True)
    years_in_business = db.Column(db.Integer, nullable=True)
    avg_service_time = db.Column(db.Integer, default=20)  # Average service time in minutes
    gst_number = db.Column(db.String(15), nullable=True)
    website = db.Column(db.String(100), nullable=True)
    additional_info = db.Column(db.String(500), nullable=True)
    registration_fee = db.Column(db.Integer, default=500)
    payment_status = db.Column(db.String(20), default='Pending')
    payment_id = db.Column(db.String(50), nullable=True)
    admin_username = db.Column(db.String(50), nullable=True)
    admin_password = db.Column(db.String(50), nullable=True)
    status = db.Column(db.String(20), default='Pending')  # Pending, Approved, Rejected
    submitted_time = db.Column(db.DateTime, default=datetime.now)
    reviewed_time = db.Column(db.DateTime, nullable=True)

# Initialize database and sample data
def init_db():
    with app.app_context():
        try:
            db.create_all()
            print("✅ Database tables created")
        except Exception as e:
            print(f"❌ Database init error: {e}")
            return  # Exit early if tables can't be created
        
        try:
            # Add service centers from approved registrations
            approved_registrations = ServiceCenterRegistration.query.filter_by(status='Approved').all()
            for reg in approved_registrations:
                # Check if service center already exists
                existing = ServiceCenter.query.filter_by(name=reg.center_name, location=f"{reg.city}, {reg.state}").first()
                if not existing:
                    new_center = ServiceCenter(
                        name=reg.center_name,
                        category=reg.organization_type,
                        location=f"{reg.city}, {reg.state}",
                        avg_service_time=15
                    )
                    db.session.add(new_center)
                    db.session.commit()
                    
                    # Create admin for this center if credentials exist
                    if reg.admin_username and reg.admin_password:
                        admin_exists = Admin.query.filter_by(username=reg.admin_username).first()
                        if not admin_exists:
                            new_admin = Admin(
                                username=reg.admin_username,
                                email=reg.email,
                                password=reg.admin_password,  # Already hashed during approval
                                service_center_id=new_center.id
                            )
                            db.session.add(new_admin)
                            db.session.commit()
        except Exception as e:
            print(f"⚠️ Error processing approved registrations: {e}")
        
        # Add default service centers only if none exist
        try:
            if ServiceCenter.query.count() == 0:
                centers = [
                    # Medical Clinics (Nagpur coordinates)
                    ServiceCenter(name='APOLLO CLINIC', category='Medical Clinic', location='Civil Lines, Nagpur', latitude=21.1458, longitude=79.0882, avg_service_time=20),
                    ServiceCenter(name='The Nagpur Clinic', category='Medical Clinic', location='Dharampeth, Nagpur', latitude=21.1466, longitude=79.0882, avg_service_time=18),
                    ServiceCenter(name='Nagpur Clinic', category='Medical Clinic', location='Sitabuldi, Nagpur', latitude=21.1498, longitude=79.0806, avg_service_time=15),
                    ServiceCenter(name='MOTHER INDIA FETAL MEDICINE CENTRE', category='Medical Clinic', location='Ramdaspeth, Nagpur', latitude=21.1307, longitude=79.0711, avg_service_time=25),
                    ServiceCenter(name='Ashvatam Clinic', category='Medical Clinic', location='Sadar, Nagpur', latitude=21.1509, longitude=79.0831, avg_service_time=18),
                    ServiceCenter(name='Apna Clinic', category='Medical Clinic', location='Gandhibagh, Nagpur', latitude=21.1540, longitude=79.0849, avg_service_time=15),
                    ServiceCenter(name='Dr.Agrawal Multispeciality Clinic', category='Medical Clinic', location='Wardha Road, Nagpur', latitude=21.1180, longitude=79.0510, avg_service_time=22),
                    ServiceCenter(name='Shree Clinic', category='Medical Clinic', location='Manish Nagar, Nagpur', latitude=21.1220, longitude=79.0420, avg_service_time=15),
                    ServiceCenter(name='Sai Clinic', category='Medical Clinic', location='Pratap Nagar, Nagpur', latitude=21.1650, longitude=79.0900, avg_service_time=18),
                    ServiceCenter(name='Suyash Clinic', category='Medical Clinic', location='Laxmi Nagar, Nagpur', latitude=21.1700, longitude=79.0950, avg_service_time=15),
                    ServiceCenter(name='INC CLINIC NAGPUR', category='Medical Clinic', location='Dhantoli, Nagpur', latitude=21.1350, longitude=79.0750, avg_service_time=20),
                    # Mobile Service Centers
                    ServiceCenter(name='Apple Service - NGRT Systems', category='Mobile Service', location='Civil Lines, Nagpur', latitude=21.1458, longitude=79.0882, avg_service_time=30),
                    ServiceCenter(name='Samsung Service - The Mobile Magic', category='Mobile Service', location='Sitabuldi, Nagpur', latitude=21.1498, longitude=79.0806, avg_service_time=25),
                    ServiceCenter(name='Samsung Service - Spectrum Marketing', category='Mobile Service', location='Dharampeth, Nagpur', latitude=21.1466, longitude=79.0882, avg_service_time=25),
                    ServiceCenter(name='Samsung Service - Karuna Management', category='Mobile Service', location='Rambagh Layout, Nagpur', latitude=21.1400, longitude=79.0700, avg_service_time=25),
                    ServiceCenter(name='Samsung CE - Akshay Refrigeration', category='Mobile Service', location='Somalwada, Nagpur', latitude=21.1600, longitude=79.1000, avg_service_time=28),
                    ServiceCenter(name='vivo India Service Center', category='Mobile Service', location='Sadar, Nagpur', latitude=21.1509, longitude=79.0831, avg_service_time=22),
                    ServiceCenter(name='vivo & iQOO Service Center', category='Mobile Service', location='Medical Chowk, Nagpur', latitude=21.1520, longitude=79.0840, avg_service_time=22),
                    ServiceCenter(name='OPPO Service Center', category='Mobile Service', location='Sitabuldi, Nagpur', latitude=21.1498, longitude=79.0806, avg_service_time=22),
                ]
                db.session.add_all(centers)
                db.session.commit()
                print("✅ Added default service centers")
        except Exception as e:
            print(f"⚠️ Error adding service centers: {e}")
        
        # Add admins
        try:
            if Admin.query.count() == 0:
                admins = [
                    Admin(username='apollo@admin.com', password=generate_password_hash('admin123'), service_center_id=1),
                    Admin(username='nagpurclinic@admin.com', password=generate_password_hash('admin123'), service_center_id=2),
                    Admin(username='localclinic@admin.com', password=generate_password_hash('admin123'), service_center_id=3),
                    Admin(username='motherindia@admin.com', password=generate_password_hash('admin123'), service_center_id=4),
                    Admin(username='ashvatam@admin.com', password=generate_password_hash('admin123'), service_center_id=5),
                    Admin(username='apna@admin.com', password=generate_password_hash('admin123'), service_center_id=6),
                    Admin(username='agrawal@admin.com', password=generate_password_hash('admin123'), service_center_id=7),
                    Admin(username='shree@admin.com', password=generate_password_hash('admin123'), service_center_id=8),
                    Admin(username='sai@admin.com', password=generate_password_hash('admin123'), service_center_id=9),
                    Admin(username='suyash@admin.com', password=generate_password_hash('admin123'), service_center_id=10),
                    Admin(username='inc@admin.com', password=generate_password_hash('admin123'), service_center_id=11),
                    Admin(username='apple@admin.com', password=generate_password_hash('admin123'), service_center_id=12),
                    Admin(username='samsung1@admin.com', password=generate_password_hash('admin123'), service_center_id=13),
                    Admin(username='samsung2@admin.com', password=generate_password_hash('admin123'), service_center_id=14),
                    Admin(username='samsung3@admin.com', password=generate_password_hash('admin123'), service_center_id=15),
                    Admin(username='samsung4@admin.com', password=generate_password_hash('admin123'), service_center_id=16),
                    Admin(username='vivo@admin.com', password=generate_password_hash('admin123'), service_center_id=17),
                    Admin(username='vivoiqoo@admin.com', password=generate_password_hash('admin123'), service_center_id=18),
                    Admin(username='oppo@admin.com', password=generate_password_hash('admin123'), service_center_id=19),
                ]
                db.session.add_all(admins)
                db.session.commit()
                print("✅ Added admin accounts")
        except Exception as e:
            print(f"⚠️ Error adding admins: {e}")
        
        # Add demo users
        try:
            if User.query.count() == 0:
                demo_users = [
                    User(name='Rahul Sharma', mobile='9876543210', email='rahul@demo.com', password=generate_password_hash('demo123')),
                    User(name='Priya Patel', mobile='9876543211', email='priya@demo.com', password=generate_password_hash('demo123')),
                    User(name='Amit Kumar', mobile='9876543212', email='amit@demo.com', password=generate_password_hash('demo123')),
                    User(name='Sneha Deshmukh', mobile='9876543213', email='sneha@demo.com', password=generate_password_hash('demo123')),
                    User(name='Vikram Singh', mobile='9876543214', email='vikram@demo.com', password=generate_password_hash('demo123')),
                ]
                db.session.add_all(demo_users)
                db.session.commit()
                print("✅ Added demo users")
        except Exception as e:
            print(f"⚠️ Error adding demo users: {e}")
        
        # Add super admin
        try:
            if SuperAdmin.query.count() == 0:
                super_admin = SuperAdmin(
                    username='superadmin@queueflow.com',
                    password=generate_password_hash('superadmin123'),
                    email='superadmin@queueflow.com'
                )
                db.session.add(super_admin)
                db.session.commit()
                print("✅ Added super admin")
        except Exception as e:
            print(f"⚠️ Error adding super admin: {e}")

# Helper functions
def get_active_token_for_user(user_id):
    return Token.query.filter_by(user_id=user_id).filter(
        Token.status.in_(['PendingPayment', 'Active', 'Serving'])
    ).first()

def get_queue_count(center_id):
    return Token.query.filter_by(service_center_id=center_id, status='Active', is_walkin=False).count()

def get_serving_token(center_id):
    return Token.query.filter_by(service_center_id=center_id, status='Serving', is_walkin=False).first()

def get_walkin_queue_count(center_id):
    return Token.query.filter_by(service_center_id=center_id, status='Active', is_walkin=True).count()

def get_walkin_serving_token(center_id):
    return Token.query.filter_by(service_center_id=center_id, status='Serving', is_walkin=True).first()

def generate_token_number(center_id):
    today = datetime.now().date()
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

def calculate_travel_time(user_lat, user_lon, center_lat, center_lon):
    """Calculate travel time in minutes based on distance (assuming 30 km/h avg speed)"""
    if not all([user_lat, user_lon, center_lat, center_lon]):
        return 10  # Default 10 minutes if location not available
    
    # Haversine formula to calculate distance
    from math import radians, sin, cos, sqrt, atan2
    
    R = 6371  # Earth radius in km
    lat1, lon1, lat2, lon2 = map(radians, [user_lat, user_lon, center_lat, center_lon])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    distance = R * c
    
    # Assume average speed of 30 km/h in city traffic
    travel_time = (distance / 30) * 60  # Convert to minutes
    return int(travel_time)

def expire_old_tokens():
    # Expire pending payment tokens after 2 hours
    expiry_time = datetime.now() - timedelta(hours=2)
    expired_tokens = Token.query.filter(
        Token.status == 'PendingPayment',
        Token.created_time < expiry_time
    ).all()
    for token in expired_tokens:
        token.status = 'Expired'
    
    # Expire active tokens after 4 hours (if admin never called them)
    active_expiry_time = datetime.now() - timedelta(hours=4)
    old_active_tokens = Token.query.filter(
        Token.status == 'Active',
        Token.created_time < active_expiry_time
    ).all()
    for token in old_active_tokens:
        token.status = 'Expired'
    
    db.session.commit()

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
                      <p>Hello {user_name},</p>
                      <p>Your token has been confirmed at <strong>{center_name}</strong>.</p>
                      
                      <div style="background: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0;">
                        <h3 style="color: #2DD4BF; margin-top: 0;">Token Details</h3>
                        <p style="font-size: 24px; font-weight: bold; color: #333; margin: 10px 0;">Token: {token_number}</p>
                        <p style="margin: 5px 0;"><strong>Service Center:</strong> {center_name}</p>
                      </div>
                      
                      <div style="background: #fff3cd; padding: 15px; border-left: 4px solid #ffc107; margin: 20px 0;">
                        <h3 style="color: #856404; margin-top: 0;">⏰ Important Timings</h3>
                        <p style="margin: 8px 0;"><strong>🏠 Leave Home By:</strong> {leave_time.strftime('%I:%M %p')}</p>
                        <p style="margin: 8px 0;"><strong>🏥 Reach Counter By:</strong> {reach_time.strftime('%I:%M %p')}</p>
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

# Ensure database is initialized before first request
@app.before_request
def initialize_database():
    if not hasattr(app, 'db_initialized'):
        try:
            with app.app_context():
                db.create_all()
                # Add default data only if tables are empty
                try:
                    if ServiceCenter.query.count() == 0:
                        init_db()
                except Exception as e:
                    print(f"⚠️ Error checking/initializing data: {e}")
                app.db_initialized = True
        except Exception as e:
            print(f"❌ Database initialization error: {e}")
            app.db_initialized = True  # Mark as initialized to prevent infinite loops

# Routes - User Module
@app.route('/')
def index():
    return render_template('home.html')

@app.route('/register-center', methods=['GET', 'POST'])
def register_center():
    if request.method == 'POST':
        phone = request.form.get('phone')
        password = request.form.get('password')
        
        if ServiceCenterRegistration.query.filter_by(phone=phone).first():
            flash('Phone number already registered!', 'danger')
            return redirect(url_for('register_center'))
        
        # Get avg_service_time safely
        try:
            avg_service_time = int(request.form.get('avg_service_time', 20))
        except (ValueError, TypeError):
            avg_service_time = 20
        
        registration = ServiceCenterRegistration(
            center_name=request.form.get('center_name'),
            organization_type=request.form.get('organization_type'),
            owner_name=request.form.get('owner_name'),
            email=request.form.get('email'),
            phone=phone,
            password=generate_password_hash(password),
            alternate_phone=request.form.get('alternate_phone'),
            city=request.form.get('city'),
            state=request.form.get('state'),
            pincode=request.form.get('pincode'),
            address=request.form.get('address'),
            latitude=float(request.form.get('latitude')) if request.form.get('latitude') else None,
            longitude=float(request.form.get('longitude')) if request.form.get('longitude') else None,
            business_hours=request.form.get('business_hours'),
            counters=request.form.get('counters') or None,
            daily_customers=request.form.get('daily_customers') or None,
            years_in_business=request.form.get('years_in_business') or None,
            avg_service_time=avg_service_time,
            gst_number=request.form.get('gst_number'),
            website=request.form.get('website'),
            additional_info=request.form.get('additional_info'),
            status='Pending',
            payment_status='Pending'
        )
        db.session.add(registration)
        db.session.commit()
        
        return redirect(url_for('registration_payment', reg_id=registration.id))
    
    return render_template('register_center.html')

@app.route('/registration-payment/<int:reg_id>', methods=['GET', 'POST'])
def registration_payment(reg_id):
    registration = ServiceCenterRegistration.query.get_or_404(reg_id)
    
    if registration.payment_status == 'Completed':
        flash('Payment already completed!', 'info')
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        payment_id = f"PAY{registration.id}{int(datetime.now().timestamp())}"
        registration.payment_status = 'Completed'
        registration.payment_id = payment_id
        db.session.commit()
        
        flash('Registration fee paid successfully! You can now login to track status.', 'success')
        return render_template('register_center_success.html', 
                             email=registration.email, 
                             phone=registration.phone,
                             payment_id=payment_id)
    
    return render_template('registration_payment.html', registration=registration)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        try:
            name = request.form.get('name', '').strip()
            mobile = request.form.get('mobile', '').strip()
            email = request.form.get('email', '').strip()
            password = request.form.get('password', '')
            
            print(f"📝 Registration attempt: name={name}, mobile={mobile}, email={email}")
            
            if not all([name, mobile, email, password]):
                flash('All fields are required!', 'danger')
                return redirect(url_for('register'))
            
            # Check if mobile already exists
            existing_user = User.query.filter_by(mobile=mobile).first()
            if existing_user:
                flash('Mobile number already registered!', 'danger')
                return redirect(url_for('register'))
            
            # Create new user
            user = User(
                name=name, 
                mobile=mobile, 
                email=email, 
                password=generate_password_hash(password)
            )
            db.session.add(user)
            db.session.commit()
            
            print(f"✅ User registered successfully: {mobile}")
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Registration error: {type(e).__name__}: {str(e)}")
            import traceback
            traceback.print_exc()
            flash(f'Registration failed: {str(e)}', 'danger')
            return redirect(url_for('register'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        mobile = request.form['mobile']
        password = request.form['password']
        
        # Check if service center owner
        owner = ServiceCenterRegistration.query.filter_by(phone=mobile).first()
        if owner and check_password_hash(owner.password, password):
            session['owner_id'] = owner.id
            session['owner_name'] = owner.owner_name
            return redirect(url_for('owner_dashboard'))
        
        # Check if regular user
        user = User.query.filter_by(mobile=mobile).first()
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['user_name'] = user.name
            return redirect(url_for('services'))
        
        flash('Invalid credentials!', 'danger')
    
    return render_template('login.html')

@app.route('/services')
def services():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    expire_old_tokens()
    
    # Get category filter
    category_filter = request.args.get('category')
    
    if category_filter:
        # Filter by category (partial match)
        centers = ServiceCenter.query.filter(ServiceCenter.category.contains(category_filter)).all()
    else:
        centers = ServiceCenter.query.all()
    
    active_token = get_active_token_for_user(session['user_id'])
    
    center_data = []
    for center in centers:
        queue_count = get_queue_count(center.id)
        center_data.append({
            'center': center,
            'queue_count': queue_count,
            'can_request': queue_count < 15,
            'is_new': center.id > 19
        })
    
    return render_template('services.html', centers=center_data, active_token=active_token)

@app.route('/request_token/<int:center_id>')
def request_token(center_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Check if user already has active token
    if get_active_token_for_user(session['user_id']):
        flash('You already have an active token!', 'warning')
        return redirect(url_for('services'))
    
    # Check queue limit
    if get_queue_count(center_id) >= 15:
        flash('Queue is full! Please try later.', 'warning')
        return redirect(url_for('services'))
    
    # Create token
    token_number = generate_token_number(center_id)
    token = Token(
        user_id=session['user_id'],
        service_center_id=center_id,
        token_number=token_number,
        status='PendingPayment'
    )
    db.session.add(token)
    db.session.commit()
    
    return redirect(url_for('payment', token_id=token.id))

@app.route('/payment/<int:token_id>', methods=['GET', 'POST'])
def payment(token_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    token = Token.query.get_or_404(token_id)
    if token.user_id != session['user_id']:
        flash('Unauthorized access!', 'danger')
        return redirect(url_for('services'))
    
    if request.method == 'POST':
        token.status = 'Active'
        db.session.commit()
        
        flash('Payment successful! Your token is confirmed.', 'success')
        
        # Send timing alert email (non-blocking)
        try:
            user = User.query.get(session['user_id'])
            if user.email:
                center = ServiceCenter.query.get(token.service_center_id)
                serving_token = get_serving_token(center.id)
                
                position = Token.query.filter(
                    Token.service_center_id == center.id,
                    Token.status == 'Active',
                    Token.is_walkin == False,
                    Token.id < token.id
                ).count() + 1
                if serving_token:
                    position += 1
                
                # Calculate wait time and travel time
                user = User.query.get(session['user_id'])
                travel_time = calculate_travel_time(user.latitude, user.longitude, center.latitude, center.longitude)
                
                wait_time = calculate_wait_time(center.id, position)
                service_start_time = datetime.now() + timedelta(minutes=wait_time)
                
                leave_time = service_start_time - timedelta(minutes=travel_time + 5)
                if leave_time < datetime.now():
                    leave_time = datetime.now()
                
                reach_time = leave_time + timedelta(minutes=travel_time)
                
                send_timing_alert(user.email, user.name, token.token_number, center.name, leave_time, reach_time)
        except Exception as e:
            print(f"Email sending failed: {e}")
        
        return redirect(url_for('queue_status', token_id=token.id))
    
    return render_template('payment.html', token=token)

@app.route('/queue_status/<int:token_id>')
def queue_status(token_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    token = Token.query.get_or_404(token_id)
    if token.user_id != session['user_id']:
        flash('Unauthorized access!', 'danger')
        return redirect(url_for('services'))
    
    # Auto-expire tokens older than 4 hours that are still Active
    if token.status == 'Active':
        hours_since_creation = (datetime.now() - token.created_time).total_seconds() / 3600
        if hours_since_creation > 4:
            token.status = 'Expired'
            db.session.commit()
            flash('Your token has expired. Please book a new token.', 'warning')
            return redirect(url_for('services'))
    
    # If token is not Active or Serving, redirect
    if token.status not in ['Active', 'Serving']:
        flash(f'Token is {token.status.lower()}.', 'info')
        return redirect(url_for('services'))
    
    serving_token = get_serving_token(token.service_center_id)
    
    position = 0
    if token.status == 'Active':
        position = Token.query.filter(
            Token.service_center_id == token.service_center_id,
            Token.status == 'Active',
            Token.is_walkin == False,
            Token.id < token.id
        ).count() + 1
        if serving_token:
            position += 1
    
    # Calculate travel time based on user and center location
    user = User.query.get(session['user_id'])
    center = ServiceCenter.query.get(token.service_center_id)
    travel_time = calculate_travel_time(user.latitude, user.longitude, center.latitude, center.longitude)
    
    # For 1st person: Book + 10 min ready + travel
    if position <= 1:
        leave_time = token.created_time + timedelta(minutes=10)
        reach_counter_time = leave_time + timedelta(minutes=travel_time)
    else:
        # For others: Calculate when counter becomes free
        # Counter free = 1st person reach time + (position-1) * service time
        first_token = Token.query.filter(
            Token.service_center_id == token.service_center_id,
            Token.status.in_(['Active', 'Serving']),
            Token.is_walkin == False
        ).order_by(Token.id).first()
        
        if first_token:
            # Estimate when first person reaches (their booking + 10 + travel)
            first_user = User.query.get(first_token.user_id)
            first_travel = calculate_travel_time(first_user.latitude, first_user.longitude, center.latitude, center.longitude)
            first_reach = first_token.created_time + timedelta(minutes=10 + first_travel)
            
            # Counter free after all previous people finish
            counter_free_time = first_reach + timedelta(minutes=(position - 1) * center.avg_service_time)
        else:
            # Fallback if first token not found
            counter_free_time = token.created_time + timedelta(minutes=(position - 1) * center.avg_service_time)
        
        # Reach counter when it becomes free
        reach_counter_time = counter_free_time
        
        # Leave = reach - travel
        leave_time = reach_counter_time - timedelta(minutes=travel_time)
        
        # If leave time is in past, leave now
        if leave_time < datetime.now():
            leave_time = datetime.now()
    
    # Calculate wait time for display only
    wait_time = 0
    
    return render_template('queue_status.html', 
                         token=token, 
                         serving_token=serving_token,
                         position=position,
                         wait_time=wait_time,
                         travel_time=travel_time,
                         leave_time=leave_time,
                         reach_counter_time=reach_counter_time)

@app.route('/cancel_token/<int:token_id>')
def cancel_token(token_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    token = Token.query.get_or_404(token_id)
    if token.user_id != session['user_id']:
        flash('Unauthorized access!', 'danger')
        return redirect(url_for('services'))
    
    if token.status == 'PendingPayment':
        token.status = 'Expired'
        db.session.commit()
        flash('Token cancelled successfully.', 'info')
    
    return redirect(url_for('services'))

@app.route('/history')
def user_history():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    tokens = Token.query.filter_by(user_id=session['user_id']).filter(
        Token.status.in_(['Completed', 'Expired'])
    ).order_by(Token.created_time.desc()).all()
    
    return render_template('user_history.html', tokens=tokens, datetime=datetime)

@app.route('/profile', methods=['GET', 'POST'])
def user_profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user = User.query.get(session['user_id'])
    
    if request.method == 'POST':
        user.name = request.form.get('name')
        user.email = request.form.get('email')
        user.address = request.form.get('address')
        
        lat = request.form.get('latitude')
        lon = request.form.get('longitude')
        if lat and lon:
            user.latitude = float(lat)
            user.longitude = float(lon)
        
        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('user_profile'))
    
    return render_template('user_profile.html', user=user)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# Password Reset Routes
@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        mobile = request.form.get('mobile', '').strip()
        email = request.form.get('email', '').strip()
        
        if not mobile:
            flash('Mobile number is required!', 'danger')
            return render_template('forgot_password.html')
        
        user = User.query.filter_by(mobile=mobile).first()
        if not user:
            flash('Mobile number not registered!', 'danger')
            return render_template('forgot_password.html')
        
        # Check if user has email
        if not user.email:
            flash('No email associated with this account. Please contact support.', 'warning')
            return render_template('forgot_password.html')
        
        # Verify email matches
        if email and user.email != email:
            flash('Email does not match our records!', 'danger')
            return render_template('forgot_password.html')
        
        # Generate reset token
        reset_token = secrets.token_urlsafe(32)
        user.reset_token = reset_token
        user.reset_token_expiry = datetime.now() + timedelta(hours=1)
        db.session.commit()
        
        # Flash success immediately (don't wait for email)
        flash('Password reset link sent to your email!', 'success')
        
        # Send email (non-blocking)
        reset_link = url_for('reset_password', token=reset_token, _external=True)
        print(f"🔐 Attempting to send reset email to {user.email}")
        
        try:
            send_reset_email(user.email, reset_link, "User")
        except Exception as e:
            print(f"❌ Email send failed: {e}")
        
        return redirect(url_for('login'))
    
    return render_template('forgot_password.html')

@app.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    user = User.query.filter_by(reset_token=token).first()
    
    if not user or not user.reset_token_expiry or user.reset_token_expiry < datetime.now():
        flash('Invalid or expired reset link!', 'danger')
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        new_password = request.form.get('password')
        user.password = generate_password_hash(new_password)
        user.reset_token = None
        user.reset_token_expiry = None
        db.session.commit()
        
        flash('Password reset successful! Please login.', 'success')
        return redirect(url_for('login'))
    
    return render_template('reset_password.html', token=token)

@app.route('/admin/forgot-password', methods=['GET', 'POST'])
def admin_forgot_password():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        
        admin = Admin.query.filter_by(username=username).first()
        if admin and admin.email == email:
            # Generate reset token
            reset_token = secrets.token_urlsafe(32)
            admin.reset_token = reset_token
            admin.reset_token_expiry = datetime.now() + timedelta(hours=1)
            db.session.commit()
            
            # Send email
            reset_link = url_for('admin_reset_password', token=reset_token, _external=True)
            if send_reset_email(email, reset_link, "Admin"):
                flash('Password reset link sent to your email!', 'success')
            else:
                flash('Email not configured. Contact super admin.', 'warning')
            return redirect(url_for('admin_login'))
        else:
            flash('Invalid username or email!', 'danger')
    
    return render_template('admin_forgot_password.html')

@app.route('/admin/reset-password/<token>', methods=['GET', 'POST'])
def admin_reset_password(token):
    admin = Admin.query.filter_by(reset_token=token).first()
    
    if not admin or not admin.reset_token_expiry or admin.reset_token_expiry < datetime.now():
        flash('Invalid or expired reset link!', 'danger')
        return redirect(url_for('admin_login'))
    
    if request.method == 'POST':
        new_password = request.form.get('password')
        admin.password = generate_password_hash(new_password)
        admin.reset_token = None
        admin.reset_token_expiry = None
        db.session.commit()
        
        flash('Password reset successful! Please login.', 'success')
        return redirect(url_for('admin_login'))
    
    return render_template('admin_reset_password.html', token=token)

# Service Center Owner Dashboard
@app.route('/owner/dashboard')
def owner_dashboard():
    if 'owner_id' not in session:
        return redirect(url_for('login'))
    
    owner = ServiceCenterRegistration.query.get(session['owner_id'])
    return render_template('owner_dashboard.html', registration=owner)

# Routes - Admin Module
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        admin = Admin.query.filter_by(username=username).first()
        if admin and check_password_hash(admin.password, password):
            session['admin_id'] = admin.id
            session['admin_center_id'] = admin.service_center_id
            return redirect(url_for('admin_dashboard'))
        
        flash('Invalid credentials!', 'danger')
    
    return render_template('admin_login.html')

@app.route('/admin/dashboard')
def admin_dashboard():
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))
    
    center_id = session['admin_center_id']
    center = ServiceCenter.query.get(center_id)
    
    # Online Queue (Counter 1)
    serving_token = get_serving_token(center_id)
    waiting_tokens = Token.query.filter_by(
        service_center_id=center_id, 
        status='Active',
        is_walkin=False
    ).order_by(Token.id).all()
    
    # Walk-in Queue (Counter 2)
    walkin_serving_token = get_walkin_serving_token(center_id)
    walkin_waiting_tokens = Token.query.filter_by(
        service_center_id=center_id,
        status='Active',
        is_walkin=True
    ).order_by(Token.id).all()
    
    # Calculate when next token can be called (Online)
    can_call_next = True
    next_call_time = None
    
    next_token = Token.query.filter_by(
        service_center_id=center_id,
        status='Active',
        is_walkin=False
    ).order_by(Token.id).first()
    
    if next_token:
        position = Token.query.filter(
            Token.service_center_id == center_id,
            Token.status == 'Active',
            Token.is_walkin == False,
            Token.id < next_token.id
        ).count() + 1
        
        wait_time = position * center.avg_service_time
        expected_arrival = next_token.created_time + timedelta(minutes=wait_time)
        
        if datetime.now() < expected_arrival:
            can_call_next = False
            next_call_time = expected_arrival
    
    return render_template('admin_dashboard.html', 
                         center=center,
                         serving_token=serving_token,
                         waiting_tokens=waiting_tokens,
                         walkin_serving_token=walkin_serving_token,
                         walkin_waiting_tokens=walkin_waiting_tokens,
                         can_call_next=can_call_next,
                         next_call_time=next_call_time,
                         datetime=datetime)

@app.route('/admin/history')
def admin_history():
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))
    
    center_id = session['admin_center_id']
    center = ServiceCenter.query.get(center_id)
    tokens = Token.query.filter_by(service_center_id=center_id).filter(
        Token.status.in_(['Completed', 'Expired'])
    ).order_by(Token.created_time.desc()).limit(100).all()
    
    return render_template('admin_history.html', center=center, tokens=tokens)

@app.route('/admin/call_next')
def call_next():
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))
    
    center_id = session['admin_center_id']
    center = ServiceCenter.query.get(center_id)
    
    serving_token = get_serving_token(center_id)
    if serving_token:
        serving_token.status = 'Completed'
        serving_token.completed_time = datetime.now()
    
    next_token = Token.query.filter_by(
        service_center_id=center_id,
        status='Active',
        is_walkin=False
    ).order_by(Token.id).first()
    
    if next_token:
        position = Token.query.filter(
            Token.service_center_id == center_id,
            Token.status == 'Active',
            Token.is_walkin == False,
            Token.id < next_token.id
        ).count() + 1
        
        wait_time = position * center.avg_service_time
        expected_arrival = next_token.created_time + timedelta(minutes=wait_time)
        
        if datetime.now() < expected_arrival:
            minutes_left = int((expected_arrival - datetime.now()).total_seconds() / 60)
            flash(f'Please wait {minutes_left} more minutes. User needs time to arrive at counter.', 'warning')
            return redirect(url_for('admin_dashboard'))
        
        next_token.status = 'Serving'
        db.session.commit()
        flash(f'Token {next_token.token_number} is now being served.', 'success')
    else:
        db.session.commit()
        flash('No tokens in queue.', 'info')
    
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/call_next_walkin')
def call_next_walkin():
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))
    
    center_id = session['admin_center_id']
    
    walkin_serving_token = get_walkin_serving_token(center_id)
    if walkin_serving_token:
        walkin_serving_token.status = 'Completed'
        walkin_serving_token.completed_time = datetime.now()
    
    next_token = Token.query.filter_by(
        service_center_id=center_id,
        status='Active',
        is_walkin=True
    ).order_by(Token.id).first()
    
    if next_token:
        next_token.status = 'Serving'
        db.session.commit()
        flash(f'Walk-in token {next_token.token_number} is now being served.', 'success')
    else:
        db.session.commit()
        flash('No walk-in tokens in queue.', 'info')
    
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/complete/<int:token_id>')
def complete_token(token_id):
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))
    
    token = Token.query.get_or_404(token_id)
    token.status = 'Completed'
    token.completed_time = datetime.now()
    db.session.commit()
    flash('Token marked as completed.', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/no_show/<int:token_id>', methods=['GET', 'POST'])
def no_show(token_id):
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))
    
    token = Token.query.get_or_404(token_id)
    
    if request.method == 'POST':
        reason = request.form.get('reason', '').strip()
        notes = request.form.get('notes', '').strip()
        
        if not reason:
            flash('Please provide a reason for marking as no-show.', 'danger')
            return redirect(url_for('admin_dashboard'))
        
        full_reason = reason
        if notes:
            full_reason += f" - {notes}"
        
        token.status = 'Expired'
        token.no_show_reason = full_reason
        token.no_show_time = datetime.now()
        
        user = User.query.get(token.user_id)
        user.no_show_count += 1
        
        db.session.commit()
        flash('Token marked as no-show with reason recorded.', 'warning')
        return redirect(url_for('admin_dashboard'))
    
    return render_template('no_show_form.html', token=token)

@app.route('/admin/add_walkin', methods=['GET', 'POST'])
def add_walkin():
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))
    
    center_id = session.get('admin_center_id')
    if not center_id:
        flash('Session expired. Please login again.', 'danger')
        return redirect(url_for('admin_login'))
    
    center = ServiceCenter.query.get(center_id)
    if not center:
        flash('Service center not found.', 'danger')
        return redirect(url_for('admin_login'))
    
    if request.method == 'POST':
        name = request.form.get('name', 'Walk-in Customer').strip()
        mobile = request.form.get('mobile', '').strip()
        
        if get_walkin_queue_count(center_id) >= 15:
            flash('Walk-in queue is full!', 'warning')
            return redirect(url_for('admin_dashboard'))
        
        # Create or get user
        if mobile and len(mobile) == 10:
            user = User.query.filter_by(mobile=mobile).first()
            if not user:
                user = User(name=name, mobile=mobile, password=generate_password_hash('walkin123'))
                db.session.add(user)
                db.session.commit()
        else:
            # Anonymous walk-in
            user = User(name=name, mobile=f'W{int(datetime.now().timestamp())}', email=f'walkin{int(datetime.now().timestamp())}@queueflow.com', password=generate_password_hash('walkin123'))
            db.session.add(user)
            db.session.commit()
        
        # Generate token with W prefix
        today = datetime.now().date()
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
            is_walkin=True
        )
        db.session.add(token)
        db.session.commit()
        
        flash(f'Walk-in token {token_number} created successfully!', 'success')
        return redirect(url_for('token_qr', token_number=token_number))
    
    return render_template('add_walkin.html', center=center)

@app.route('/track', methods=['GET', 'POST'])
def track_token():
    if request.method == 'POST':
        token_number = request.form.get('token_number', '').strip().upper()
        
        token = Token.query.filter_by(token_number=token_number).first()
        if not token:
            flash('Token not found!', 'danger')
            return redirect(url_for('track_token'))
        
        if token.status not in ['Active', 'Serving']:
            flash('Token is no longer active.', 'warning')
            return redirect(url_for('track_token'))
        
        return redirect(url_for('track_status', token_number=token_number))
    
    return render_template('track_token.html')

@app.route('/track/<token_number>')
def track_status(token_number):
    token = Token.query.filter_by(token_number=token_number).first_or_404()
    
    if token.is_walkin:
        serving_token = get_walkin_serving_token(token.service_center_id)
        position = 0
        if token.status == 'Active':
            position = Token.query.filter(
                Token.service_center_id == token.service_center_id,
                Token.status == 'Active',
                Token.is_walkin == True,
                Token.id < token.id
            ).count() + 1
            if serving_token:
                position += 1
    else:
        serving_token = get_serving_token(token.service_center_id)
        position = 0
        if token.status == 'Active':
            position = Token.query.filter(
                Token.service_center_id == token.service_center_id,
                Token.status == 'Active',
                Token.is_walkin == False,
                Token.id < token.id
            ).count() + 1
            if serving_token:
                position += 1
    
    wait_time = calculate_wait_time(token.service_center_id, position)
    reach_counter_time = datetime.now() + timedelta(minutes=wait_time)
    
    return render_template('track_status.html',
                         token=token,
                         serving_token=serving_token,
                         position=position,
                         wait_time=wait_time,
                         reach_counter_time=reach_counter_time)

@app.route('/admin/logout')
def admin_logout():
    session.clear()
    return redirect(url_for('admin_login'))

# Super Admin Routes
@app.route('/superadmin/login', methods=['GET', 'POST'])
def superadmin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        super_admin = SuperAdmin.query.filter_by(username=username).first()
        if super_admin and check_password_hash(super_admin.password, password):
            session['superadmin_id'] = super_admin.id
            session['superadmin_username'] = super_admin.username
            return redirect(url_for('superadmin_dashboard'))
        
        flash('Invalid credentials!', 'danger')
    
    return render_template('superadmin_login.html')

@app.route('/superadmin/dashboard')
def superadmin_dashboard():
    if 'superadmin_id' not in session:
        return redirect(url_for('superadmin_login'))
    
    pending = ServiceCenterRegistration.query.filter_by(status='Pending').order_by(ServiceCenterRegistration.submitted_time.desc()).all()
    approved = ServiceCenterRegistration.query.filter_by(status='Approved').order_by(ServiceCenterRegistration.reviewed_time.desc()).limit(10).all()
    rejected = ServiceCenterRegistration.query.filter_by(status='Rejected').order_by(ServiceCenterRegistration.reviewed_time.desc()).limit(10).all()
    
    stats = {
        'pending': ServiceCenterRegistration.query.filter_by(status='Pending').count(),
        'approved': ServiceCenterRegistration.query.filter_by(status='Approved').count(),
        'rejected': ServiceCenterRegistration.query.filter_by(status='Rejected').count(),
        'total': ServiceCenterRegistration.query.count()
    }
    
    return render_template('superadmin_dashboard.html', 
                         pending=pending, 
                         approved=approved, 
                         rejected=rejected,
                         stats=stats)

@app.route('/superadmin/registration/<int:reg_id>/approve', methods=['POST'])
def approve_registration(reg_id):
    if 'superadmin_id' not in session:
        return redirect(url_for('superadmin_login'))
    
    registration = ServiceCenterRegistration.query.get_or_404(reg_id)
    registration.status = 'Approved'
    registration.reviewed_time = datetime.now()
    
    # Create ServiceCenter entry
    try:
        avg_time = registration.avg_service_time if hasattr(registration, 'avg_service_time') and registration.avg_service_time else 20
    except:
        avg_time = 20
    
    service_center = ServiceCenter(
        name=registration.center_name,
        category=registration.organization_type,
        location=f"{registration.address}, {registration.city}, {registration.state} - {registration.pincode}",
        latitude=registration.latitude,
        longitude=registration.longitude,
        avg_service_time=avg_time
    )
    db.session.add(service_center)
    db.session.flush()  # Get the service_center.id
    
    # Generate admin credentials
    admin_username = registration.email.split('@')[0] + '@admin.com'
    admin_password = f"admin{registration.phone[-4:]}"  # admin + last 4 digits of phone
    
    # Create Admin account
    admin = Admin(
        username=admin_username,
        email=registration.email,
        password=generate_password_hash(admin_password),
        service_center_id=service_center.id
    )
    db.session.add(admin)
    
    # Store credentials in registration for owner to see
    registration.admin_username = admin_username
    registration.admin_password = admin_password  # Store plain text for display only
    
    db.session.commit()
    
    flash(f'Registration approved! Service center "{registration.center_name}" is now live. Admin login: {admin_username} / {admin_password}', 'success')
    return redirect(url_for('superadmin_dashboard'))

@app.route('/superadmin/registration/<int:reg_id>/reject', methods=['POST'])
def reject_registration(reg_id):
    if 'superadmin_id' not in session:
        return redirect(url_for('superadmin_login'))
    
    registration = ServiceCenterRegistration.query.get_or_404(reg_id)
    registration.status = 'Rejected'
    registration.reviewed_time = datetime.now()
    db.session.commit()
    
    flash(f'Registration for {registration.center_name} rejected.', 'warning')
    return redirect(url_for('superadmin_dashboard'))

@app.route('/superadmin/logout')
def superadmin_logout():
    session.clear()
    return redirect(url_for('superadmin_login'))

@app.route('/superadmin/center/<int:center_id>/delete', methods=['POST'])
def superadmin_delete_center(center_id):
    if 'superadmin_id' not in session:
        return redirect(url_for('superadmin_login'))
    
    center = ServiceCenter.query.get_or_404(center_id)
    center_name = center.name
    
    # Delete all tokens for this center
    Token.query.filter_by(service_center_id=center_id).delete()
    
    # Delete admin accounts for this center
    Admin.query.filter_by(service_center_id=center_id).delete()
    
    # Delete the service center
    db.session.delete(center)
    db.session.commit()
    
    flash(f'Service center "{center_name}" deleted successfully!', 'success')
    return redirect(url_for('superadmin_manage_centers'))

@app.route('/superadmin/manage-centers')
def superadmin_manage_centers():
    if 'superadmin_id' not in session:
        return redirect(url_for('superadmin_login'))
    
    try:
        centers = ServiceCenter.query.order_by(ServiceCenter.id).all()
        return render_template('superadmin_manage_centers.html', centers=centers)
    except Exception as e:
        flash(f'Error loading centers: {str(e)}', 'danger')
        return redirect(url_for('superadmin_dashboard'))

@app.route('/admin/delete-center', methods=['POST'])
def admin_delete_center():
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))
    
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
    return redirect(url_for('home'))

@app.route('/token-qr/<token_number>')
def token_qr(token_number):
    """Generate QR code for token tracking"""
    token = Token.query.filter_by(token_number=token_number).first_or_404()
    
    # Generate tracking URL
    track_url = url_for('track_status', token_number=token_number, _external=True)
    
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
    
    return render_template('token_qr.html', 
                         token=token, 
                         qr_code=img_base64,
                         track_url=track_url)

@app.route('/admin/analytics')
def admin_analytics():
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))
    
    center_id = session['admin_center_id']
    center = ServiceCenter.query.get(center_id)
    
    if not center:
        flash('Service center not found', 'danger')
        return redirect(url_for('admin_dashboard'))
    
    today = datetime.now().date()
    
    # Daily customers
    daily_customers = Token.query.filter(
        Token.service_center_id == center_id,
        db.func.date(Token.created_time) == today
    ).count()
    
    # Last 7 days
    last_7_days = []
    for i in range(6, -1, -1):
        date = today - timedelta(days=i)
        count = Token.query.filter(
            Token.service_center_id == center_id,
            db.func.date(Token.created_time) == date
        ).count()
        last_7_days.append({'date': date.strftime('%a'), 'count': count})
    
    # Online vs Walk-in
    total_tokens = Token.query.filter_by(service_center_id=center_id).count()
    walkin_tokens = Token.query.filter_by(service_center_id=center_id, is_walkin=True).count()
    online_tokens = total_tokens - walkin_tokens
    
    analytics = {
        'daily_customers': daily_customers,
        'last_7_days': last_7_days,
        'peak_hours': [],
        'online_tokens': online_tokens,
        'walkin_tokens': walkin_tokens,
        'total_tokens': total_tokens,
        'avg_wait_time': center.avg_service_time
    }
    
    return render_template('admin_analytics.html', center=center, analytics=analytics)

@app.route('/test-email-config')
def test_email_config():
    """Test endpoint to verify email configuration"""
    config_status = {
        'MAIL_SERVER': app.config.get('MAIL_SERVER', 'NOT SET'),
        'MAIL_PORT': app.config.get('MAIL_PORT', 'NOT SET'),
        'MAIL_USERNAME': app.config.get('MAIL_USERNAME', 'NOT SET'),
        'MAIL_PASSWORD_LENGTH': len(app.config.get('MAIL_PASSWORD', '')),
        'MAIL_USE_TLS': app.config.get('MAIL_USE_TLS', 'NOT SET'),
    }
    return f"<pre>{config_status}</pre><br><p>Password configured: {bool(app.config.get('MAIL_PASSWORD'))}</p>"

@app.route('/test-send-email')
def test_send_email():
    """Test endpoint to actually send an email"""
    brevo_key = os.getenv('BREVO_API_KEY', '')
    if not brevo_key:
        return f"<h2>Email Send Test</h2><p>❌ BREVO_API_KEY not configured in environment variables</p>"
    
    try:
        test_link = "https://digital-queue-management-system-1.onrender.com/"
        result = send_reset_email('teltumdesahil441@gmail.com', test_link, 'Test')
        return f"<h2>Email Send Test</h2><p>Result: {'SUCCESS ✅' if result else 'FAILED ❌'}</p><p>Check Render logs and your email inbox</p>"
    except Exception as e:
        return f"<h2>Email Send Test</h2><p>ERROR: {str(e)}</p><p>Check Render logs for full traceback</p>"

@app.route('/migrate-db-add-column')
def migrate_db():
    """Manual migration endpoint to add missing columns"""
    results = []
    try:
        with db.engine.connect() as conn:
            # Check and add avg_service_time column
            try:
                result = conn.execute(db.text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_name='service_center_registrations' AND column_name='avg_service_time'"
                ))
                if not result.fetchone():
                    conn.execute(db.text(
                        "ALTER TABLE service_center_registrations ADD COLUMN avg_service_time INTEGER DEFAULT 20"
                    ))
                    conn.commit()
                    results.append("✅ Added avg_service_time column to service_center_registrations")
                else:
                    results.append("ℹ️ avg_service_time column already exists in service_center_registrations")
            except Exception as e:
                results.append(f"⚠️ avg_service_time: {str(e)}")
            
            # Check and add completed_time column to tokens table
            try:
                result = conn.execute(db.text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_name='tokens' AND column_name='completed_time'"
                ))
                if not result.fetchone():
                    conn.execute(db.text(
                        "ALTER TABLE tokens ADD COLUMN completed_time TIMESTAMP"
                    ))
                    conn.commit()
                    results.append("✅ Added completed_time column to tokens table")
                else:
                    results.append("ℹ️ completed_time column already exists in tokens table")
            except Exception as e:
                results.append(f"⚠️ completed_time: {str(e)}")
            
            # Check and add user location columns
            try:
                result = conn.execute(db.text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_name='users' AND column_name='address'"
                ))
                if not result.fetchone():
                    conn.execute(db.text(
                        "ALTER TABLE users ADD COLUMN address VARCHAR(200)"
                    ))
                    conn.execute(db.text(
                        "ALTER TABLE users ADD COLUMN latitude FLOAT"
                    ))
                    conn.execute(db.text(
                        "ALTER TABLE users ADD COLUMN longitude FLOAT"
                    ))
                    conn.commit()
                    results.append("✅ Added address, latitude, longitude columns to users table")
                else:
                    results.append("ℹ️ User location columns already exist")
            except Exception as e:
                results.append(f"⚠️ User location: {str(e)}")
            
            # Check and add service center location columns
            try:
                result = conn.execute(db.text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_name='service_centers' AND column_name='latitude'"
                ))
                if not result.fetchone():
                    conn.execute(db.text(
                        "ALTER TABLE service_centers ADD COLUMN latitude FLOAT"
                    ))
                    conn.execute(db.text(
                        "ALTER TABLE service_centers ADD COLUMN longitude FLOAT"
                    ))
                    conn.commit()
                    results.append("✅ Added latitude, longitude columns to service_centers table")
                else:
                    results.append("ℹ️ Service center location columns already exist")
            except Exception as e:
                results.append(f"⚠️ Service center location: {str(e)}")
            
            # Check and add registration location columns
            try:
                result = conn.execute(db.text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_name='service_center_registrations' AND column_name='latitude'"
                ))
                if not result.fetchone():
                    conn.execute(db.text(
                        "ALTER TABLE service_center_registrations ADD COLUMN latitude FLOAT"
                    ))
                    conn.execute(db.text(
                        "ALTER TABLE service_center_registrations ADD COLUMN longitude FLOAT"
                    ))
                    conn.commit()
                    results.append("✅ Added latitude, longitude columns to service_center_registrations table")
                else:
                    results.append("ℹ️ Registration location columns already exist")
            except Exception as e:
                results.append(f"⚠️ Registration location: {str(e)}")
            
            return "<h2>Migration Results</h2>" + "".join([f"<p>{r}</p>" for r in results])
    except Exception as e:
        return f"<h2>Migration Error</h2><p>❌ {str(e)}</p>"

@app.route('/admin/generate-demo-data')
def generate_demo_data():
    """Generate demo tokens for analytics testing"""
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))
    
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
        return redirect(url_for('admin_analytics'))
    except Exception as e:
        flash(f'Error generating demo data: {str(e)}', 'danger')
        return redirect(url_for('admin_dashboard'))

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 5000))
    debug_mode = os.getenv('FLASK_ENV', 'production') == 'development'
    app.run(host='0.0.0.0', port=port, debug=debug_mode)
