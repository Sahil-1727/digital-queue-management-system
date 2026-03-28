import secrets
from flask import render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import timedelta

from blueprints.auth import auth_bp
from extensions import db
from models import User, Admin, SuperAdmin, ServiceCenterRegistration
from utils import get_ist_now, send_reset_email
from auth import owner_required


@auth_bp.route('/register', methods=['GET', 'POST'])
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
                    return redirect(url_for('auth.register'))

                # Check if mobile already exists
                existing_user = User.query.filter_by(mobile=mobile).first()
                if existing_user:
                    flash('Mobile number already registered!', 'danger')
                    return redirect(url_for('auth.register'))

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
                return redirect(url_for('auth.login'))

            except Exception as e:
                db.session.rollback()
                print(f"❌ Registration error: {type(e).__name__}: {str(e)}")
                import traceback
                traceback.print_exc()
                flash(f'Registration failed: {str(e)}', 'danger')
                return redirect(url_for('auth.register'))

        return render_template('auth/register.html')
    except Exception as e:
        print(f"❌ Register page error: {e}")
        import traceback
        traceback.print_exc()
        return f"<h1>Error loading registration page</h1><pre>{str(e)}</pre>", 500


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    try:
        if request.method == 'POST':
            identifier = request.form['mobile'].strip()
            password = request.form['password']

            # Check if service center owner
            owner = ServiceCenterRegistration.query.filter(
                (ServiceCenterRegistration.phone == identifier) |
                (ServiceCenterRegistration.email == identifier)
            ).first()
            if owner and check_password_hash(owner.password, password):
                session['owner_id'] = owner.id
                session['owner_name'] = owner.owner_name
                return redirect(url_for('auth.owner_dashboard'))

            # Check if regular user
            user = User.query.filter(
                (User.mobile == identifier) |
                (User.email == identifier)
            ).first()
            if user and check_password_hash(user.password, password):
                session['user_id'] = user.id
                session['user_name'] = user.name
                return redirect(url_for('user.services'))

            flash('Invalid credentials!', 'danger')

        return render_template('auth/login.html')
    except Exception as e:
        print(f"❌ Login page error: {e}")
        import traceback
        traceback.print_exc()
        return f"<h1>Error loading login page</h1><pre>{str(e)}</pre>", 500


@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login'))


@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        mobile = request.form.get('mobile', '').strip()
        email = request.form.get('email', '').strip()

        if not mobile:
            flash('Mobile number is required!', 'danger')
            return render_template('auth/forgot_password.html')

        user = User.query.filter_by(mobile=mobile).first()
        if not user:
            flash('Mobile number not registered!', 'danger')
            return render_template('auth/forgot_password.html')

        # Check if user has email
        if not user.email:
            flash('No email associated with this account. Please contact support.', 'warning')
            return render_template('auth/forgot_password.html')

        # Verify email matches
        if email and user.email != email:
            flash('Email does not match our records!', 'danger')
            return render_template('auth/forgot_password.html')

        # Generate reset token
        reset_token = secrets.token_urlsafe(32)
        user.reset_token = reset_token
        user.reset_token_expiry = get_ist_now() + timedelta(hours=1)
        db.session.commit()

        # Flash success immediately (don't wait for email)
        flash('Password reset link sent to your email!', 'success')

        # Send email (non-blocking)
        reset_link = url_for('auth.reset_password', token=reset_token, _external=True)
        print(f"🔐 Attempting to send reset email to {user.email}")

        try:
            send_reset_email(user.email, reset_link, "User")
        except Exception as e:
            print(f"❌ Email send failed: {e}")

        return redirect(url_for('auth.login'))

    return render_template('auth/forgot_password.html')


@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    user = User.query.filter_by(reset_token=token).first()

    if not user or not user.reset_token_expiry or user.reset_token_expiry < get_ist_now():
        flash('Invalid or expired reset link!', 'danger')
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        new_password = request.form.get('password')
        user.password = generate_password_hash(new_password)
        user.reset_token = None
        user.reset_token_expiry = None
        db.session.commit()

        flash('Password reset successful! Please login.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/reset_password.html', token=token)


@auth_bp.route('/admin/forgot-password', methods=['GET', 'POST'])
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
            reset_link = url_for('auth.admin_reset_password', token=reset_token, _external=True)
            if send_reset_email(email, reset_link, "Admin"):
                flash('Password reset link sent to your email!', 'success')
            else:
                flash('Email not configured. Contact super admin.', 'warning')
            return redirect(url_for('admin.admin_login'))
        else:
            flash('Invalid username or email!', 'danger')

    return render_template('admin/admin_forgot_password.html')


@auth_bp.route('/admin/reset-password/<token>', methods=['GET', 'POST'])
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


@auth_bp.route('/owner/dashboard')
@owner_required
def owner_dashboard():
    owner = ServiceCenterRegistration.query.get(session['owner_id'])
    return render_template('user/owner_dashboard.html', registration=owner)
