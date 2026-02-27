from functools import wraps
from flask import session, redirect, url_for, flash

def user_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login to access this page.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_id' not in session:
            flash('Admin access required.', 'danger')
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

def superadmin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'superadmin_id' not in session:
            flash('Super admin access required.', 'danger')
            return redirect(url_for('superadmin_login'))
        return f(*args, **kwargs)
    return decorated_function

def owner_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'owner_id' not in session:
            flash('Owner access required.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function
