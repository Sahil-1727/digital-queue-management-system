from flask import render_template, request, redirect, url_for, session, flash
from datetime import timedelta

from blueprints.user import user_bp
from extensions import db
from models import Token, ServiceCenter, User
from utils import (
    get_ist_now, get_ist_now_aware, utc_to_ist,
    get_active_token_for_user, get_queue_count, get_serving_token,
    get_walkin_serving_token, get_walkin_queue_count,
    generate_token_number, calculate_wait_time,
    calculate_travel_time, get_user_location,
    expire_old_tokens, recalculate_queue_times, send_timing_alert, IST
)
from auth import user_required


@user_bp.route('/services')
@user_required
def services():
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

    return render_template('user/services.html', centers=center_data, active_token=active_token)


@user_bp.route('/request_token/<int:center_id>')
def request_token(center_id):
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    # Check if user already has active token
    if get_active_token_for_user(session['user_id']):
        flash('You already have an active token!', 'warning')
        return redirect(url_for('user.services'))

    # Check queue limit
    if get_queue_count(center_id) >= 15:
        flash('Queue is full! Please try later.', 'warning')
        return redirect(url_for('user.services'))

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

    return redirect(url_for('user.payment', token_id=token.id))


@user_bp.route('/payment/<int:token_id>', methods=['GET', 'POST'])
def payment(token_id):
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    token = Token.query.get_or_404(token_id)
    if token.user_id != session['user_id']:
        flash('Unauthorized access!', 'danger')
        return redirect(url_for('user.services'))

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

        if travel_time is None:
            travel_time = 30  # Default fallback: 30 min when ORS API unavailable or coords missing

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
                if first_travel is None:
                    first_travel = 30  # Default fallback

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

        return redirect(url_for('user.queue_status', token_id=token.id))

    return render_template('user/payment.html', token=token)


@user_bp.route('/queue_status/<int:token_id>')
def queue_status(token_id):
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    # Auto-expire late tokens before checking status
    expire_old_tokens()

    token = Token.query.get_or_404(token_id)
    if token.user_id != session['user_id']:
        flash('Unauthorized access!', 'danger')
        return redirect(url_for('user.services'))

    if token.status not in ['Active', 'Serving']:
        flash(f'Token is {token.status.lower()}.', 'info')
        return redirect(url_for('user.services'))

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

    # ONLY use stored times from database (calculated at payment)
    leave_time = token.leave_time
    reach_counter_time = token.reach_time

    # Convert UTC to IST
    leave_time = utc_to_ist(leave_time)
    reach_counter_time = utc_to_ist(reach_counter_time)

    # Calculate travel time from stored times
    travel_time = None
    if leave_time and reach_counter_time:
        travel_time = int((reach_counter_time - leave_time).total_seconds() / 60)

    return render_template('user/queue_status.html',
                           token=token,
                           serving_token=serving_token,
                           position=position,
                           wait_time=0,
                           travel_time=travel_time,
                           leave_time=leave_time,
                           reach_counter_time=reach_counter_time,
                           IST=IST)


@user_bp.route('/cancel_token/<int:token_id>')
def cancel_token(token_id):
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    token = Token.query.get_or_404(token_id)
    if token.user_id != session['user_id']:
        flash('Unauthorized access!', 'danger')
        return redirect(url_for('user.services'))

    if token.status in ['PendingPayment', 'Active']:
        center_id = token.service_center_id
        token.status = 'Expired'
        token.no_show_reason = 'Cancelled by user'
        token.no_show_time = get_ist_now()
        db.session.commit()

        # Recalculate queue times for remaining tokens
        recalculate_queue_times(center_id)

        flash('Token cancelled successfully.', 'info')

    return redirect(url_for('user.services'))


@user_bp.route('/history')
def user_history():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    tokens = Token.query.filter_by(user_id=session['user_id']).filter(
        Token.status.in_(['Completed', 'Expired'])
    ).order_by(Token.created_time.desc()).limit(50).all()

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

    return render_template('user/user_history.html', tokens=enriched_tokens, IST=IST)


@user_bp.route('/profile', methods=['GET', 'POST'])
def user_profile():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

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
        return redirect(url_for('user.user_profile'))

    return render_template('user/user_profile.html', user=user)


@user_bp.route('/service-detail/<int:center_id>')
def service_detail(center_id):
    center = ServiceCenter.query.get_or_404(center_id)
    queue_count = get_queue_count(center.id)
    serving_token = get_serving_token(center.id)

    # Check if user has active token
    active_token = None
    if 'user_id' in session:
        active_token = get_active_token_for_user(session['user_id'])

    # Get related centers (same category)
    related_centers = ServiceCenter.query.filter(
        ServiceCenter.category == center.category,
        ServiceCenter.id != center.id
    ).limit(3).all()

    return render_template('user/service_details.html',
                           center=center,
                           queue_count=queue_count,
                           serving_token=serving_token,
                           active_token=active_token,
                           related_centers=related_centers)


@user_bp.route('/track', methods=['GET', 'POST'])
def track_token():
    if request.method == 'POST':
        token_number = request.form.get('token_number', '').strip().upper()

        token = Token.query.filter_by(token_number=token_number).first()
        if not token:
            flash('Token not found!', 'danger')
            return redirect(url_for('user.track_token'))

        if token.status not in ['Active', 'Serving']:
            flash('Token is no longer active.', 'warning')
            return redirect(url_for('user.track_token'))

        return redirect(url_for('user.track_status', token_number=token_number))

    return render_template('user/track_token.html')


@user_bp.route('/track/<token_number>')
def track_status(token_number):
    token = Token.query.filter_by(token_number=token_number).first_or_404()
    center = ServiceCenter.query.get(token.service_center_id)

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

    # Calculate wait time based on position
    wait_time = calculate_wait_time(token.service_center_id, position)

    # Use IST timezone-aware current time
    current_time_ist = get_ist_now_aware()
    reach_counter_time = current_time_ist + timedelta(minutes=wait_time)

    return render_template('user/track_status.html',
                           token=token,
                           serving_token=serving_token,
                           position=position,
                           wait_time=wait_time,
                           reach_counter_time=reach_counter_time,
                           IST=IST)


@user_bp.route('/register-center', methods=['GET', 'POST'])
def register_center():
    try:
        from werkzeug.security import generate_password_hash as _hash
        from models import ServiceCenterRegistration
        if request.method == 'POST':
            phone = request.form.get('phone')
            password = request.form.get('password')

            if ServiceCenterRegistration.query.filter_by(phone=phone).first():
                flash('Phone number already registered!', 'danger')
                return redirect(url_for('user.register_center'))

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
                password=_hash(password),
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

            return redirect(url_for('user.registration_payment', reg_id=registration.id))

        return render_template('user/register_center.html')
    except Exception as e:
        print(f"❌ Register center error: {e}")
        import traceback
        traceback.print_exc()
        return f"<h1>Error loading center registration</h1><pre>{str(e)}</pre>", 500


@user_bp.route('/registration-payment/<int:reg_id>', methods=['GET', 'POST'])
def registration_payment(reg_id):
    from models import ServiceCenterRegistration
    from datetime import datetime
    registration = ServiceCenterRegistration.query.get_or_404(reg_id)

    if registration.payment_status == 'Completed':
        flash('Payment already completed!', 'info')
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        payment_id = f"PAY{registration.id}{int(datetime.now().timestamp())}"
        registration.payment_status = 'Completed'
        registration.payment_id = payment_id
        db.session.commit()

        flash('Registration fee paid successfully! You can now login to track status.', 'success')
        return render_template('user/register_center_success.html',
                               email=registration.email,
                               phone=registration.phone,
                               payment_id=payment_id)

    return render_template('user/registration_payment.html', registration=registration)
