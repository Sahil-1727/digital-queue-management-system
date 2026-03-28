from datetime import datetime
from extensions import db


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
