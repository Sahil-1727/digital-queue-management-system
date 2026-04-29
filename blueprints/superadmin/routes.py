from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from models import User, ServiceCenter, Admin, Token, SuperAdmin, ServiceCenterRegistration
from extensions import db
from auth import superadmin_required

superadmin_bp = Blueprint('superadmin', __name__, url_prefix='/superadmin')


@superadmin_bp.route('/login', methods=['GET', 'POST'])
def superadmin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        super_admin = SuperAdmin.query.filter_by(username=username).first()
        if super_admin and check_password_hash(super_admin.password, password):
            session['superadmin_id'] = super_admin.id
            session['superadmin_username'] = super_admin.username
            return redirect(url_for('superadmin.superadmin_dashboard'))
        
        flash('Invalid credentials!', 'danger')
    
    return render_template('superadmin/superadmin_login.html')


@superadmin_bp.route('/dashboard')
@superadmin_required
def superadmin_dashboard():
    
    pending = ServiceCenterRegistration.query.filter_by(status='Pending').order_by(ServiceCenterRegistration.submitted_time.desc()).all()
    approved = ServiceCenterRegistration.query.filter_by(status='Approved').order_by(ServiceCenterRegistration.reviewed_time.desc()).limit(10).all()
    rejected = ServiceCenterRegistration.query.filter_by(status='Rejected').order_by(ServiceCenterRegistration.reviewed_time.desc()).limit(10).all()
    
    stats = {
        'pending': ServiceCenterRegistration.query.filter_by(status='Pending').count(),
        'approved': ServiceCenterRegistration.query.filter_by(status='Approved').count(),
        'rejected': ServiceCenterRegistration.query.filter_by(status='Rejected').count(),
        'total': ServiceCenterRegistration.query.count()
    }
    
    return render_template('superadmin/superadmin_dashboard.html', 
                         pending=pending, 
                         approved=approved, 
                         rejected=rejected,
                         stats=stats)


@superadmin_bp.route('/registration/<int:reg_id>/approve', methods=['POST'])
def approve_registration(reg_id):
    if 'superadmin_id' not in session:
        return redirect(url_for('superadmin.superadmin_login'))
    
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
    return redirect(url_for('superadmin.superadmin_dashboard'))


@superadmin_bp.route('/registration/<int:reg_id>/reject', methods=['POST'])
def reject_registration(reg_id):
    if 'superadmin_id' not in session:
        return redirect(url_for('superadmin.superadmin_login'))
    
    registration = ServiceCenterRegistration.query.get_or_404(reg_id)
    registration.status = 'Rejected'
    registration.reviewed_time = datetime.now()
    db.session.commit()
    
    flash(f'Registration for {registration.center_name} rejected.', 'warning')
    return redirect(url_for('superadmin.superadmin_dashboard'))


@superadmin_bp.route('/admins')
def superadmin_admins():
    if 'superadmin_id' not in session:
        return redirect(url_for('superadmin.superadmin_login'))
    
    try:
        admins = Admin.query.join(ServiceCenter).order_by(ServiceCenter.name).all()
        return render_template('superadmin/superadmin_admins.html', admins=admins)
    except Exception as e:
        flash(f'Error loading admins: {str(e)}', 'danger')
        return redirect(url_for('superadmin.superadmin_dashboard'))


@superadmin_bp.route('/admin/<int:admin_id>/edit', methods=['GET', 'POST'])
def superadmin_edit_admin(admin_id):
    if 'superadmin_id' not in session:
        return redirect(url_for('superadmin.superadmin_login'))
    
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
            return redirect(url_for('superadmin.superadmin_admins'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating details: {str(e)}', 'danger')
    
    return render_template('superadmin/superadmin_edit_admin.html', admin=admin, center=center)


@superadmin_bp.route('/analytics')
def superadmin_analytics():
    """Super Admin analytics page"""
    if 'superadmin_id' not in session:
        return redirect(url_for('superadmin.superadmin_login'))
    
    return render_template('superadmin/superadmin_analytics.html')


@superadmin_bp.route('/logout')
def superadmin_logout():
    session.clear()
    return redirect(url_for('superadmin.superadmin_login'))


@superadmin_bp.route('/center/<int:center_id>/delete', methods=['POST'])
def superadmin_delete_center(center_id):
    if 'superadmin_id' not in session:
        return redirect(url_for('superadmin.superadmin_login'))
    
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
    return redirect(url_for('superadmin.superadmin_manage_centers'))


@superadmin_bp.route('/manage-centers')
def superadmin_manage_centers():
    if 'superadmin_id' not in session:
        return redirect(url_for('superadmin.superadmin_login'))
    
    try:
        centers = ServiceCenter.query.order_by(ServiceCenter.id).all()
        return render_template('superadmin/superadmin_manage_centers.html', centers=centers)
    except Exception as e:
        flash(f'Error loading centers: {str(e)}', 'danger')
        return redirect(url_for('superadmin.superadmin_dashboard'))


@superadmin_bp.route('/api/analytics')
def api_superadmin_analytics():
    """JSON endpoint for super admin system-wide analytics"""
    if 'superadmin_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    today = datetime.now().date()
    
    # System-wide stats
    total_centers = ServiceCenter.query.count()
    total_users = User.query.count()
    daily_tokens = Token.query.filter(db.func.date(Token.created_time) == today).count()
    
    # Last 7 days trend (system-wide) — single GROUP BY query
    seven_days_ago = today - timedelta(days=6)
    trend_rows = db.session.query(
        db.func.date(Token.created_time).label('day'),
        db.func.count(Token.id).label('cnt')
    ).filter(
        db.func.date(Token.created_time) >= seven_days_ago
    ).group_by('day').all()
    trend_map = {str(row.day): row.cnt for row in trend_rows}
    trend_data = []
    for i in range(6, -1, -1):
        date = today - timedelta(days=i)
        trend_data.append({'date': date.strftime('%a'), 'count': trend_map.get(str(date), 0)})
    
    # Online vs Walk-in (system-wide)
    total_tokens = Token.query.count()
    walkin_tokens = Token.query.filter_by(is_walkin=True).count()
    online_tokens = total_tokens - walkin_tokens
    
    # Status breakdown (system-wide)
    completed = Token.query.filter_by(status='Completed').count()
    no_show = Token.query.filter_by(status='No Show').count()
    expired = Token.query.filter_by(status='Expired').count()
    
    # Top performing centers
    top_centers = db.session.query(
        ServiceCenter.name,
        db.func.count(Token.id).label('token_count')
    ).join(Token).group_by(ServiceCenter.id).order_by(db.desc('token_count')).limit(5).all()
    
    return jsonify({
        'total_centers': total_centers,
        'total_users': total_users,
        'daily_tokens': daily_tokens,
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
        'top_centers': [{'name': name, 'count': count} for name, count in top_centers]
    })
