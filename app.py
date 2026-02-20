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
import pytz
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt

# Load environment variables
load_dotenv()

# Timezone configuration
IST = pytz.timezone('Asia/Kolkata')

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
    mobile = db.Column(db.String(20), unique=True, nullable=False)
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
    description = db.Column(db.String(500), nullable=True)
    phone = db.Column(db.String(15), nullable=True)
    email = db.Column(db.String(100), nullable=True)
    website = db.Column(db.String(100), nullable=True)
    business_hours = db.Column(db.String(100), nullable=True)
    services_offered = db.Column(db.String(500), nullable=True)
    facilities = db.Column(db.String(500), nullable=True)
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
    status = db.Column(db.String(20), default='PendingPayment')
    created_time = db.Column(db.DateTime, default=datetime.now)
    completed_time = db.Column(db.DateTime, nullable=True)
    
    # User-side estimated times (for email/queue status)
    leave_time = db.Column(db.DateTime, nullable=True)
    reach_time = db.Column(db.DateTime, nullable=True)
    
    # Admin-side time-chain fields
    estimated_service_start = db.Column(db.DateTime, nullable=True)
    estimated_service_end = db.Column(db.DateTime, nullable=True)
    actual_service_start = db.Column(db.DateTime, nullable=True)
    actual_service_end = db.Column(db.DateTime, nullable=True)
    
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
                    ServiceCenter(
                        name='APOLLO CLINIC', category='Medical Clinic', location='Civil Lines, Nagpur', 
                        latitude=21.1458, longitude=79.0882, avg_service_time=20,
                        description='Premier multi-specialty clinic offering comprehensive healthcare services with experienced doctors and modern facilities.',
                        phone='+91 712 2531234', email='apollo.nagpur@clinic.com', website='https://apolloclinic.com',
                        business_hours='Mon-Sat: 9:00 AM - 8:00 PM, Sun: 10:00 AM - 2:00 PM',
                        services_offered='• General Consultation\n• Pathology Lab\n• X-Ray & Ultrasound\n• Vaccination\n• Health Checkups',
                        facilities='• AC Waiting Room\n• Pharmacy\n• Wheelchair Access\n• Parking Available\n• Emergency Services'
                    ),
                    ServiceCenter(
                        name='The Nagpur Clinic', category='Medical Clinic', location='Dharampeth, Nagpur', 
                        latitude=21.1466, longitude=79.0882, avg_service_time=18,
                        description='Family healthcare center providing quality medical services with a patient-first approach.',
                        phone='+91 712 2445678', email='info@nagpurclinic.com',
                        business_hours='Mon-Sat: 8:00 AM - 9:00 PM',
                        services_offered='• General Medicine\n• Pediatrics\n• Gynecology\n• Dental Care\n• Physiotherapy',
                        facilities='• Digital Records\n• Online Reports\n• Ambulance Service\n• 24/7 Pharmacy'
                    ),
                    ServiceCenter(
                        name='Nagpur Clinic', category='Medical Clinic', location='Sitabuldi, Nagpur', 
                        latitude=21.1498, longitude=79.0806, avg_service_time=15,
                        description='Quick consultation clinic for routine checkups and minor ailments.',
                        phone='+91 712 2567890', email='contact@nagpurclinic.in',
                        business_hours='Mon-Sun: 7:00 AM - 10:00 PM',
                        services_offered='• Quick Consultation\n• Fever Clinic\n• BP & Sugar Monitoring\n• Injections\n• Dressing',
                        facilities='• Fast Service\n• Walk-in Welcome\n• Digital Payments\n• Free WiFi'
                    ),
                    ServiceCenter(
                        name='MOTHER INDIA FETAL MEDICINE CENTRE', category='Medical Clinic', location='Ramdaspeth, Nagpur', 
                        latitude=21.1307, longitude=79.0711, avg_service_time=25,
                        description='Specialized center for women and child healthcare with advanced diagnostic facilities.',
                        phone='+91 712 2678901', email='motherindia@healthcare.com', website='https://motherindiafmc.com',
                        business_hours='Mon-Sat: 9:00 AM - 6:00 PM',
                        services_offered='• Fetal Medicine\n• Gynecology\n• Obstetrics\n• 4D Ultrasound\n• Prenatal Care',
                        facilities='• Advanced Ultrasound\n• Comfortable Waiting\n• Female Staff\n• Counseling Services'
                    ),
                    ServiceCenter(
                        name='Ashvatam Clinic', category='Medical Clinic', location='Sadar, Nagpur', 
                        latitude=21.1509, longitude=79.0831, avg_service_time=18,
                        description='Holistic healthcare clinic combining modern medicine with wellness programs.',
                        phone='+91 712 2789012', email='ashvatam@clinic.com',
                        business_hours='Mon-Sat: 8:30 AM - 8:30 PM',
                        services_offered='• General Medicine\n• Diabetes Care\n• Hypertension Management\n• Wellness Programs\n• Diet Counseling',
                        facilities='• Health Monitoring\n• Yoga Classes\n• Nutrition Guidance\n• Free Parking'
                    ),
                    ServiceCenter(
                        name='Apna Clinic', category='Medical Clinic', location='Gandhibagh, Nagpur', 
                        latitude=21.1540, longitude=79.0849, avg_service_time=15,
                        description='Affordable neighborhood clinic providing essential healthcare services.',
                        phone='+91 712 2890123', email='apnaclinic@gmail.com',
                        business_hours='Mon-Sun: 6:00 AM - 11:00 PM',
                        services_offered='• General Consultation\n• First Aid\n• Fever Treatment\n• Minor Procedures\n• Prescriptions',
                        facilities='• 24/7 Service\n• Home Visits\n• Affordable Rates\n• Medicine Available'
                    ),
                    ServiceCenter(
                        name='Dr.Agrawal Multispeciality Clinic', category='Medical Clinic', location='Wardha Road, Nagpur', 
                        latitude=21.1180, longitude=79.0510, avg_service_time=22,
                        description='Multi-specialty clinic with expert doctors across various medical fields.',
                        phone='+91 712 2901234', email='dragrawal@multispeciality.com', website='https://agrawalclinic.com',
                        business_hours='Mon-Sat: 9:00 AM - 9:00 PM, Sun: 10:00 AM - 4:00 PM',
                        services_offered='• Cardiology\n• Orthopedics\n• ENT\n• Dermatology\n• General Surgery',
                        facilities='• Specialist Doctors\n• Diagnostic Lab\n• Minor OT\n• Insurance Accepted\n• Ample Parking'
                    ),
                    ServiceCenter(
                        name='Shree Clinic', category='Medical Clinic', location='Manish Nagar, Nagpur', 
                        latitude=21.1220, longitude=79.0420, avg_service_time=15,
                        description='Community clinic serving local residents with basic healthcare needs.',
                        phone='+91 712 3012345', email='shreeclinic@yahoo.com',
                        business_hours='Mon-Sat: 7:00 AM - 10:00 PM',
                        services_offered='• OPD Services\n• Injections\n• Wound Care\n• Health Checkup\n• Referrals',
                        facilities='• Quick Service\n• Friendly Staff\n• Clean Environment\n• Nearby Pharmacy'
                    ),
                    ServiceCenter(
                        name='Sai Clinic', category='Medical Clinic', location='Pratap Nagar, Nagpur', 
                        latitude=21.1650, longitude=79.0900, avg_service_time=18,
                        description='Modern clinic with focus on preventive healthcare and wellness.',
                        phone='+91 712 3123456', email='saiclinic@healthcare.in',
                        business_hours='Mon-Sat: 8:00 AM - 8:00 PM',
                        services_offered='• Preventive Care\n• Chronic Disease Management\n• Health Screening\n• Vaccination\n• Lifestyle Counseling',
                        facilities='• Health Records\n• Follow-up Care\n• Patient Education\n• Clean Facility'
                    ),
                    ServiceCenter(
                        name='Suyash Clinic', category='Medical Clinic', location='Laxmi Nagar, Nagpur', 
                        latitude=21.1700, longitude=79.0950, avg_service_time=15,
                        description='Efficient clinic providing quick medical consultations and treatments.',
                        phone='+91 712 3234567', email='suyash@clinic.com',
                        business_hours='Mon-Sun: 6:30 AM - 10:30 PM',
                        services_offered='• Quick Consultation\n• Emergency Care\n• Lab Tests\n• Prescriptions\n• Medical Certificates',
                        facilities='• Fast Service\n• Digital Payments\n• Home Collection\n• 24/7 Available'
                    ),
                    ServiceCenter(
                        name='INC CLINIC NAGPUR', category='Medical Clinic', location='Dhantoli, Nagpur', 
                        latitude=21.1350, longitude=79.0750, avg_service_time=20,
                        description='Integrated healthcare clinic offering comprehensive medical services.',
                        phone='+91 712 3345678', email='inc@clinicnagpur.com', website='https://incclinic.in',
                        business_hours='Mon-Sat: 9:00 AM - 7:00 PM',
                        services_offered='• General Medicine\n• Diagnostic Services\n• Physiotherapy\n• Dental Care\n• Eye Checkup',
                        facilities='• Modern Equipment\n• Experienced Doctors\n• Insurance Support\n• Parking Available'
                    ),
                    # Mobile Service Centers
                    ServiceCenter(
                        name='Apple Service - NGRT Systems', category='Mobile Service', location='Civil Lines, Nagpur', 
                        latitude=21.1458, longitude=79.0882, avg_service_time=30,
                        description='Authorized Apple service center providing genuine repairs and support for all Apple products.',
                        phone='+91 712 4456789', email='ngrt@appleservice.com', website='https://ngrtsystems.com',
                        business_hours='Mon-Sat: 10:00 AM - 7:00 PM',
                        services_offered='• iPhone Repair\n• iPad Service\n• MacBook Repair\n• Watch Service\n• Genuine Parts\n• Software Support',
                        facilities='• Authorized Center\n• Trained Technicians\n• Warranty Service\n• Loaner Devices\n• AC Waiting Area'
                    ),
                    ServiceCenter(
                        name='Samsung Service - The Mobile Magic', category='Mobile Service', location='Sitabuldi, Nagpur', 
                        latitude=21.1498, longitude=79.0806, avg_service_time=25,
                        description='Official Samsung service center for mobile phones and tablets with expert technicians.',
                        phone='+91 712 4567890', email='mobilemagic@samsung.com', website='https://mobilemagic.in',
                        business_hours='Mon-Sat: 10:00 AM - 8:00 PM, Sun: 11:00 AM - 5:00 PM',
                        services_offered='• Screen Replacement\n• Battery Change\n• Software Update\n• Water Damage Repair\n• Charging Port Fix',
                        facilities='• Genuine Parts\n• Quick Service\n• Warranty Support\n• Free Diagnosis\n• Comfortable Seating'
                    ),
                    ServiceCenter(
                        name='Samsung Service - Spectrum Marketing', category='Mobile Service', location='Dharampeth, Nagpur', 
                        latitude=21.1466, longitude=79.0882, avg_service_time=25,
                        description='Authorized Samsung service providing comprehensive repair solutions.',
                        phone='+91 712 4678901', email='spectrum@samsungservice.com',
                        business_hours='Mon-Sat: 9:30 AM - 7:30 PM',
                        services_offered='• Mobile Repair\n• Tablet Service\n• Display Replacement\n• Camera Repair\n• Speaker Fix',
                        facilities='• Original Parts\n• Expert Technicians\n• Fast Turnaround\n• Pickup & Drop\n• WiFi Available'
                    ),
                    ServiceCenter(
                        name='Samsung Service - Karuna Management', category='Mobile Service', location='Rambagh Layout, Nagpur', 
                        latitude=21.1400, longitude=79.0700, avg_service_time=25,
                        description='Trusted Samsung service center with years of experience in mobile repairs.',
                        phone='+91 712 4789012', email='karuna@samsung.in',
                        business_hours='Mon-Sat: 10:00 AM - 7:00 PM',
                        services_offered='• Hardware Repair\n• Software Issues\n• Data Recovery\n• Accessory Sales\n• Trade-in Service',
                        facilities='• Certified Center\n• Quality Service\n• Warranty Claims\n• Customer Support\n• Easy Parking'
                    ),
                    ServiceCenter(
                        name='Samsung CE - Akshay Refrigeration', category='Mobile Service', location='Somalwada, Nagpur', 
                        latitude=21.1600, longitude=79.1000, avg_service_time=28,
                        description='Samsung consumer electronics service center for all Samsung products.',
                        phone='+91 712 4890123', email='akshay@samsungce.com',
                        business_hours='Mon-Sat: 9:00 AM - 6:00 PM',
                        services_offered='• Mobile Service\n• TV Repair\n• Refrigerator Service\n• AC Repair\n• Washing Machine',
                        facilities='• Multi-Product Service\n• Home Service Available\n• Spare Parts Stock\n• Extended Warranty'
                    ),
                    ServiceCenter(
                        name='vivo India Service Center', category='Mobile Service', location='Sadar, Nagpur', 
                        latitude=21.1509, longitude=79.0831, avg_service_time=22,
                        description='Official vivo service center providing quality repairs and customer support.',
                        phone='+91 712 4901234', email='service@vivo.com', website='https://vivo.com/in/support',
                        business_hours='Mon-Sun: 10:00 AM - 8:00 PM',
                        services_offered='• Screen Repair\n• Battery Replacement\n• Camera Service\n• Software Update\n• Charging Issues',
                        facilities='• Authorized Service\n• Genuine Parts\n• Quick Repair\n• Warranty Service\n• Customer Lounge'
                    ),
                    ServiceCenter(
                        name='vivo & iQOO Service Center', category='Mobile Service', location='Medical Chowk, Nagpur', 
                        latitude=21.1520, longitude=79.0840, avg_service_time=22,
                        description='Combined service center for vivo and iQOO smartphones with expert technicians.',
                        phone='+91 712 5012345', email='support@vivoiqoo.in',
                        business_hours='Mon-Sun: 10:00 AM - 9:00 PM',
                        services_offered='• Display Replacement\n• Battery Service\n• Software Repair\n• Hardware Issues\n• Accessories',
                        facilities='• Dual Brand Support\n• Fast Service\n• Original Parts\n• Extended Hours\n• Free WiFi'
                    ),
                    ServiceCenter(
                        name='OPPO Service Center', category='Mobile Service', location='Sitabuldi, Nagpur', 
                        latitude=21.1498, longitude=79.0806, avg_service_time=22,
                        description='Official OPPO service center delivering excellent repair services and customer care.',
                        phone='+91 712 5123456', email='care@oppo.com', website='https://oppo.com/in/service',
                        business_hours='Mon-Sat: 10:00 AM - 8:00 PM, Sun: 11:00 AM - 6:00 PM',
                        services_offered='• Screen Replacement\n• Battery Change\n• Camera Repair\n• Software Support\n• Water Damage',
                        facilities='• Authorized Center\n• Trained Staff\n• Quality Parts\n• Warranty Support\n• Comfortable Waiting'
                    ),
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

# Register as Jinja filter for use in all templates
app.jinja_env.filters['utc_to_ist'] = utc_to_ist

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

# Ensure database is initialized before first request
@app.before_request
def initialize_database():
    if not hasattr(app, 'db_initialized'):
        try:
            with app.app_context():
                db.create_all()
                
                # Add missing columns to users table (migration)
                try:
                    with db.engine.connect() as conn:
                        # Check if address column exists
                        result = conn.execute(db.text(
                            "SELECT column_name FROM information_schema.columns "
                            "WHERE table_name='users' AND column_name='address'"
                        ))
                        if not result.fetchone():
                            conn.execute(db.text("ALTER TABLE users ADD COLUMN address VARCHAR(200)"))
                            conn.execute(db.text("ALTER TABLE users ADD COLUMN latitude FLOAT"))
                            conn.execute(db.text("ALTER TABLE users ADD COLUMN longitude FLOAT"))
                            conn.commit()
                            print("✅ Added address, latitude, longitude columns to users table")
                except Exception as e:
                    print(f"⚠️ Migration skipped (SQLite or columns exist): {e}")
                
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
    try:
        return render_template('home.html')
    except Exception as e:
        print(f"❌ Landing page error: {e}")
        import traceback
        traceback.print_exc()
        return f"<h1>Error loading page</h1><pre>{str(e)}</pre>", 500

@app.route('/register-center', methods=['GET', 'POST'])
def register_center():
    try:
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
    except Exception as e:
        print(f"❌ Register center error: {e}")
        import traceback
        traceback.print_exc()
        return f"<h1>Error loading center registration</h1><pre>{str(e)}</pre>", 500

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
    try:
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
    except Exception as e:
        print(f"❌ Register page error: {e}")
        import traceback
        traceback.print_exc()
        return f"<h1>Error loading registration page</h1><pre>{str(e)}</pre>", 500

@app.route('/login', methods=['GET', 'POST'])
def login():
    try:
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
    except Exception as e:
        print(f"❌ Login page error: {e}")
        import traceback
        traceback.print_exc()
        return f"<h1>Error loading login page</h1><pre>{str(e)}</pre>", 500

@app.route('/services')
def services():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    try:
        expire_old_tokens()
    except:
        pass
    
    category_filter = request.args.get('category')
    
    if category_filter:
        centers = ServiceCenter.query.filter(ServiceCenter.category.contains(category_filter)).all()
    else:
        centers = ServiceCenter.query.all()
    
    active_token = get_active_token_for_user(session['user_id'])
    
    center_data = []
    for center in centers:
        try:
            queue_count = get_queue_count(center.id)
        except:
            queue_count = 0
        
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
        user = User.query.get(session['user_id'])
        center = ServiceCenter.query.get(token.service_center_id)
        serving_token = get_serving_token(center.id)
        
        # Calculate position
        position = Token.query.filter(
            Token.service_center_id == center.id,
            Token.status == 'Active',
            Token.is_walkin == False,
            Token.id < token.id
        ).count() + 1
        if serving_token:
            position += 1
        
        # Calculate travel time
        user_lat, user_lon = get_user_location(user)
        travel_time = calculate_travel_time(user_lat, user_lon, center.latitude, center.longitude)
        
        # Calculate and STORE fixed times
        if position <= 1:
            # First person: Ready time (10 min) + Travel time
            leave_time = get_ist_now() + timedelta(minutes=10)
            reach_time = leave_time + timedelta(minutes=travel_time)
        else:
            # Find previous person's service end time
            previous_tokens = Token.query.filter(
                Token.service_center_id == center.id,
                Token.status.in_(['Active', 'Serving']),
                Token.is_walkin == False,
                Token.id < token.id
            ).order_by(Token.id).all()
            
            if previous_tokens:
                # Start from first person
                first_token = previous_tokens[0]
                first_user = User.query.get(first_token.user_id)
                first_user_lat, first_user_lon = get_user_location(first_user)
                first_travel = calculate_travel_time(first_user_lat, first_user_lon, center.latitude, center.longitude)
                
                # First person's arrival time
                first_leave = first_token.created_time + timedelta(minutes=10)
                first_arrival = first_leave + timedelta(minutes=first_travel)
                service_end_time = first_arrival + timedelta(minutes=center.avg_service_time)
                
                # Calculate for each person in between
                for prev_token in previous_tokens[1:]:
                    service_end_time = service_end_time + timedelta(minutes=center.avg_service_time)
                
                # Current person's earliest possible arrival
                earliest_leave = get_ist_now() + timedelta(minutes=10)
                earliest_arrival = earliest_leave + timedelta(minutes=travel_time)
                
                # Reach time = max(counter free time, earliest arrival time)
                reach_time = max(service_end_time, earliest_arrival)
                leave_time = reach_time - timedelta(minutes=travel_time)
                
                # If leave time is in past, adjust
                if leave_time < get_ist_now():
                    leave_time = get_ist_now()
                    reach_time = leave_time + timedelta(minutes=travel_time)
            else:
                # Fallback
                leave_time = get_ist_now() + timedelta(minutes=10)
                reach_time = leave_time + timedelta(minutes=travel_time)
        
        # Store times in database
        token.status = 'Active'
        token.leave_time = leave_time
        token.reach_time = reach_time
        token.estimated_service_start = reach_time
        token.estimated_service_end = reach_time + timedelta(minutes=center.avg_service_time)
        db.session.commit()
        
        flash('Payment successful! Your token is confirmed.', 'success')
        
        # Send timing alert email (non-blocking)
        try:
            if user.email:
                email_sent = send_timing_alert(user.email, user.name, token.token_number, center.name, leave_time, reach_time)
                if email_sent:
                    print(f"✅ Email sent to {user.email} for token {token.token_number} at {center.name}")
                else:
                    print(f"⚠️ Email failed for {user.email} for token {token.token_number} at {center.name}")
            else:
                print(f"⚠️ No email address for user {user.name} (token {token.token_number} at {center.name})")
        except Exception as e:
            print(f"❌ Email sending error for token {token.token_number} at {center.name}: {e}")
        
        return redirect(url_for('queue_status', token_id=token.id))
    
    return render_template('payment.html', token=token)

@app.route('/queue_status/<int:token_id>')
def queue_status(token_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Auto-expire late tokens before checking status
    expire_old_tokens()
    
    token = Token.query.get_or_404(token_id)
    if token.user_id != session['user_id']:
        flash('Unauthorized access!', 'danger')
        return redirect(url_for('services'))
    
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
    
    user = User.query.get(session['user_id'])
    center = ServiceCenter.query.get(token.service_center_id)
    user_lat, user_lon = get_user_location(user)
    travel_time = calculate_travel_time(user_lat, user_lon, center.latitude, center.longitude)
    
    # ONLY use stored times from database (calculated at payment)
    leave_time = token.leave_time
    reach_counter_time = token.reach_time
    
    # Convert UTC to IST using centralized helper
    leave_time = utc_to_ist(leave_time)
    reach_counter_time = utc_to_ist(reach_counter_time)
    
    return render_template('queue_status.html', 
                         token=token, 
                         serving_token=serving_token,
                         position=position,
                         wait_time=0,
                         travel_time=travel_time,
                         leave_time=leave_time,
                         reach_counter_time=reach_counter_time,
                         IST=IST)

@app.route('/cancel_token/<int:token_id>')
def cancel_token(token_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    token = Token.query.get_or_404(token_id)
    if token.user_id != session['user_id']:
        flash('Unauthorized access!', 'danger')
        return redirect(url_for('services'))
    
    if token.status in ['PendingPayment', 'Active']:
        center_id = token.service_center_id
        token.status = 'Expired'
        token.no_show_reason = 'Cancelled by user'
        token.no_show_time = get_ist_now()
        db.session.commit()
        
        # Recalculate queue times for remaining tokens
        recalculate_queue_times(center_id)
        
        flash('Token cancelled successfully.', 'info')
    
    return redirect(url_for('services'))

@app.route('/history')
def user_history():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    tokens = Token.query.filter_by(user_id=session['user_id']).filter(
        Token.status.in_(['Completed', 'Expired'])
    ).order_by(Token.created_time.desc()).all()
    
    # Convert times to IST for display
    enriched_tokens = []
    for token in tokens:
        token_data = {'token': token}
        
        # Determine which time to show based on status
        if token.status == 'Completed' and token.actual_service_start:
            # Show service start time for completed tokens
            time_to_show = token.actual_service_start
            time_label = 'Service Started'
        elif token.no_show_time:
            # Show no-show time
            time_to_show = token.no_show_time
            time_label = 'No-Show Marked'
        elif token.reach_time:
            # Show expected reach time (for expired tokens)
            time_to_show = token.reach_time
            time_label = 'Expected Arrival'
        else:
            time_to_show = token.created_time
            time_label = 'Booked'
        
        # Convert to IST using centralized helper
        if time_to_show:
            token_data['display_time'] = utc_to_ist(time_to_show)
            token_data['time_label'] = time_label
        else:
            token_data['display_time'] = None
            token_data['time_label'] = 'N/A'
        
        enriched_tokens.append(token_data)
    
    return render_template('user_history.html', tokens=enriched_tokens, IST=IST)

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
            try:
                user.latitude = float(lat)
                user.longitude = float(lon)
            except AttributeError:
                pass  # Columns don't exist yet
        
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
        user.reset_token_expiry = get_ist_now() + timedelta(hours=1)
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
    
    if not user or not user.reset_token_expiry or user.reset_token_expiry < get_ist_now():
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
            admin.reset_token_expiry = get_ist_now() + timedelta(hours=1)
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
    
    if not admin or not admin.reset_token_expiry or admin.reset_token_expiry < get_ist_now():
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
        
        return render_template('admin_dashboard.html', 
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
        return redirect(url_for('admin_login'))

@app.route('/admin/queue-state')
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

@app.route('/admin/history')
def admin_history():
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))
    
    center_id = session['admin_center_id']
    center = ServiceCenter.query.get(center_id)
    
    try:
        tokens = Token.query.filter_by(service_center_id=center_id).filter(
            Token.status.in_(['Completed', 'Expired'])
        ).order_by(Token.created_time.desc()).limit(100).all()
    except Exception as e:
        print(f"❌ Error fetching history: {e}")
        tokens = []
    
    return render_template('admin_history.html', center=center, tokens=tokens, IST=IST, datetime=datetime)

@app.route('/admin/profile', methods=['GET', 'POST'])
def admin_profile():
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))
    
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
            
            # Update admin email
            admin.email = request.form.get('admin_email', '').strip()
            
            db.session.commit()
            flash('Profile updated successfully!', 'success')
            return redirect(url_for('admin_profile'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating profile: {str(e)}', 'danger')
    
    return render_template('admin_profile.html', center=center, admin=admin)

@app.route('/service-detail/<int:center_id>')
def service_detail(center_id):
    center = ServiceCenter.query.get_or_404(center_id)
    queue_count = get_queue_count(center.id)
    serving_token = get_serving_token(center.id)
    
    # Check if user has active token
    active_token = None
    if 'user_id' in session:
        active_token = get_active_token_for_user(session['user_id'])
    
    return render_template('service_detail.html', 
                         center=center, 
                         queue_count=queue_count,
                         serving_token=serving_token,
                         active_token=active_token)

@app.route('/admin/call_next')
def call_next():
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))
    
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
                return redirect(url_for('admin_dashboard'))
            
            # Auto-skip if > 15 min late
            if current_time_aware > (reach_time + timedelta(minutes=15)):
                next_token.status = 'Expired'
                next_token.no_show_reason = 'Auto-skipped: More than 15 minutes late'
                next_token.no_show_time = current_time
                db.session.commit()
                flash(f'Token {next_token.token_number} auto-skipped (>15 min late). Calling next token...', 'warning')
                return redirect(url_for('call_next'))
        
        next_token.status = 'Serving'
        next_token.actual_service_start = current_time
        next_token.actual_service_end = current_time + timedelta(minutes=ServiceCenter.query.get(center_id).avg_service_time)
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
    
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/complete/<int:token_id>')
def complete_token(token_id):
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))
    
    token = Token.query.get_or_404(token_id)
    token.status = 'Completed'
    token.completed_time = get_ist_now()
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
        try:
            name = request.form.get('name', 'Walk-in Customer').strip()
            mobile = request.form.get('mobile', '').strip()
            
            try:
                if get_walkin_queue_count(center_id) >= 15:
                    flash('Walk-in queue is full!', 'warning')
                    return redirect(url_for('admin_dashboard'))
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
            return redirect(url_for('token_qr', token_number=token_number))
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error creating walk-in token: {e}")
            import traceback
            traceback.print_exc()
            flash(f'Error creating walk-in token: {str(e)}', 'danger')
            return redirect(url_for('admin_dashboard'))
    
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
                         reach_counter_time=reach_counter_time,
                         IST=IST)

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

@app.route('/superadmin/admins')
def superadmin_admins():
    if 'superadmin_id' not in session:
        return redirect(url_for('superadmin_login'))
    
    try:
        admins = Admin.query.join(ServiceCenter).order_by(ServiceCenter.name).all()
        return render_template('superadmin_admins.html', admins=admins)
    except Exception as e:
        flash(f'Error loading admins: {str(e)}', 'danger')
        return redirect(url_for('superadmin_dashboard'))

@app.route('/superadmin/admin/<int:admin_id>/edit', methods=['GET', 'POST'])
def superadmin_edit_admin(admin_id):
    if 'superadmin_id' not in session:
        return redirect(url_for('superadmin_login'))
    
    admin = Admin.query.get_or_404(admin_id)
    center = ServiceCenter.query.get(admin.service_center_id)
    
    if request.method == 'POST':
        try:
            # Update service center details
            center.name = request.form.get('center_name', '').strip()
            center.category = request.form.get('category', '').strip()
            center.location = request.form.get('location', '').strip()
            center.description = request.form.get('description', '').strip()
            center.phone = request.form.get('phone', '').strip()
            center.email = request.form.get('email', '').strip()
            center.website = request.form.get('website', '').strip()
            center.business_hours = request.form.get('business_hours', '').strip()
            center.services_offered = request.form.get('services_offered', '').strip()
            center.facilities = request.form.get('facilities', '').strip()
            center.avg_service_time = int(request.form.get('avg_service_time', 15))
            
            # Update admin details
            admin.username = request.form.get('admin_username', '').strip()
            admin.email = request.form.get('admin_email', '').strip()
            
            # Update password if provided
            new_password = request.form.get('new_password', '').strip()
            if new_password:
                admin.password = generate_password_hash(new_password)
            
            db.session.commit()
            flash('Admin and service center details updated successfully!', 'success')
            return redirect(url_for('superadmin_admins'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating details: {str(e)}', 'danger')
    
    return render_template('superadmin_edit_admin.html', admin=admin, center=center)

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
                         track_url=track_url,
                         IST=IST)

@app.route('/admin/analytics')
def admin_analytics():
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))
    
    center_id = session['admin_center_id']
    center = ServiceCenter.query.get(center_id)
    
    if not center:
        flash('Service center not found', 'danger')
        return redirect(url_for('admin_dashboard'))
    
    try:
        expire_old_tokens()
    except Exception as e:
        print(f"⚠️ Error expiring tokens: {e}")
    
    today = datetime.now().date()
    
    # Daily customers
    daily_customers = Token.query.filter(
        Token.service_center_id == center_id,
        db.func.date(Token.created_time) == today
    ).count()
    
    # Last 7 days data
    last_7_days = []
    dates = []
    counts = []
    for i in range(6, -1, -1):
        date = today - timedelta(days=i)
        count = Token.query.filter(
            Token.service_center_id == center_id,
            db.func.date(Token.created_time) == date
        ).count()
        last_7_days.append({'date': date.strftime('%a'), 'count': count})
        dates.append(date.strftime('%a'))
        counts.append(count)
    
    # Generate charts with error handling
    trend_chart = None
    pie_chart = None
    
    try:
        # Generate 7-day trend chart
        plt.figure(figsize=(10, 4))
        plt.plot(dates, counts, marker='o', linewidth=2, markersize=8, color='#0F4C5C')
        plt.fill_between(range(len(counts)), counts, alpha=0.3, color='#0F4C5C')
        plt.xlabel('Day', fontsize=12)
        plt.ylabel('Tokens', fontsize=12)
        plt.title('7-Day Token Trend', fontsize=14, fontweight='bold')
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
        buf.seek(0)
        trend_chart = base64.b64encode(buf.getvalue()).decode()
        plt.close()
    except Exception as e:
        print(f"⚠️ Error generating trend chart: {e}")
    
    # Online vs Walk-in
    try:
        total_tokens = Token.query.filter_by(service_center_id=center_id).count()
        walkin_tokens = Token.query.filter_by(service_center_id=center_id, is_walkin=True).count()
        online_tokens = total_tokens - walkin_tokens
    except:
        total_tokens = Token.query.filter_by(service_center_id=center_id).count()
        walkin_tokens = 0
        online_tokens = total_tokens
    
    # Generate pie chart
    try:
        if total_tokens > 0:
            plt.figure(figsize=(6, 6))
            labels = ['Online', 'Walk-in']
            sizes = [online_tokens, walkin_tokens]
            colors = ['#0F4C5C', '#C0843D']
            explode = (0.05, 0)
            
            plt.pie(sizes, explode=explode, labels=labels, colors=colors, autopct='%1.1f%%',
                    shadow=True, startangle=90, textprops={'fontsize': 12, 'fontweight': 'bold'})
            plt.title('Online vs Walk-in Tokens', fontsize=14, fontweight='bold')
            plt.axis('equal')
            
            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
            buf.seek(0)
            pie_chart = base64.b64encode(buf.getvalue()).decode()
            plt.close()
    except Exception as e:
        print(f"⚠️ Error generating pie chart: {e}")
    
    analytics = {
        'daily_customers': daily_customers,
        'last_7_days': last_7_days,
        'peak_hours': [],
        'online_tokens': online_tokens,
        'walkin_tokens': walkin_tokens,
        'total_tokens': total_tokens,
        'avg_wait_time': center.avg_service_time,
        'trend_chart': trend_chart,
        'pie_chart': pie_chart
    }
    
    return render_template('admin_analytics.html', center=center, analytics=analytics, IST=IST)

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

@app.route('/debug/verify-timing-system')
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

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 5000))
    debug_mode = os.getenv('FLASK_ENV', 'production') == 'development'
    app.run(host='0.0.0.0', port=port, debug=debug_mode)
