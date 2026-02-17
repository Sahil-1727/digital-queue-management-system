import re
from functools import wraps
from flask import session, redirect, url_for, flash, request
from datetime import datetime

# Input Validation Functions
def validate_mobile(mobile):
    """Validate Indian mobile number (10 digits)"""
    pattern = r'^[6-9]\d{9}$'
    return bool(re.match(pattern, str(mobile)))

def validate_email(email):
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, str(email)))

def validate_pincode(pincode):
    """Validate Indian pincode (6 digits)"""
    pattern = r'^\d{6}$'
    return bool(re.match(pattern, str(pincode)))

def validate_gst(gst):
    """Validate GST number format"""
    if not gst:
        return True  # Optional field
    pattern = r'^\d{2}[A-Z]{5}\d{4}[A-Z]{1}[A-Z\d]{1}[Z]{1}[A-Z\d]{1}$'
    return bool(re.match(pattern, str(gst)))

def sanitize_input(text, max_length=500):
    """Sanitize text input to prevent XSS"""
    if not text:
        return ""
    # Remove HTML tags and limit length
    text = re.sub(r'<[^>]*>', '', str(text))
    return text[:max_length].strip()

def validate_password_strength(password):
    """Validate password strength"""
    if len(password) < 6:
        return False, "Password must be at least 6 characters long"
    if len(password) > 128:
        return False, "Password is too long"
    return True, "Valid"

# Authentication Decorators
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login to access this page', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_id' not in session:
            flash('Admin access required', 'danger')
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

def superadmin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'superadmin_id' not in session:
            flash('Super admin access required', 'danger')
            return redirect(url_for('superadmin_login'))
        return f(*args, **kwargs)
    return decorated_function

# Security Headers
def add_security_headers(response):
    """Add security headers to response"""
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    response.headers['Content-Security-Policy'] = "default-src 'self' 'unsafe-inline' 'unsafe-eval'; img-src 'self' data: https:;"
    return response

# Rate Limiting Helper
def check_rate_limit(key, max_attempts=5, window_minutes=15):
    """Simple rate limiting check"""
    from flask import session
    attempts_key = f'attempts_{key}'
    time_key = f'time_{key}'
    
    current_time = datetime.now()
    
    if attempts_key not in session:
        session[attempts_key] = 0
        session[time_key] = current_time.isoformat()
    
    last_attempt = datetime.fromisoformat(session[time_key])
    time_diff = (current_time - last_attempt).total_seconds() / 60
    
    if time_diff > window_minutes:
        session[attempts_key] = 0
        session[time_key] = current_time.isoformat()
    
    session[attempts_key] += 1
    
    if session[attempts_key] > max_attempts:
        return False, f"Too many attempts. Please try again after {window_minutes} minutes."
    
    return True, "OK"

# Token Generation
def generate_secure_token():
    """Generate secure random token"""
    import secrets
    return secrets.token_urlsafe(32)
