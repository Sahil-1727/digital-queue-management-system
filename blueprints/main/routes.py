from flask import render_template
from blueprints.main import main_bp


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


@main_bp.route('/test-email-config')
def test_email_config():
    """Test endpoint to verify email configuration"""
    from flask import current_app
    config_status = {
        'MAIL_SERVER': current_app.config.get('MAIL_SERVER', 'NOT SET'),
        'MAIL_PORT': current_app.config.get('MAIL_PORT', 'NOT SET'),
        'MAIL_USERNAME': current_app.config.get('MAIL_USERNAME', 'NOT SET'),
        'MAIL_PASSWORD_LENGTH': len(current_app.config.get('MAIL_PASSWORD', '')),
        'MAIL_USE_TLS': current_app.config.get('MAIL_USE_TLS', 'NOT SET'),
    }
    return f"<pre>{config_status}</pre><br><p>Password configured: {bool(current_app.config.get('MAIL_PASSWORD'))}</p>"


@main_bp.route('/test-send-email')
def test_send_email():
    """Test endpoint to actually send an email"""
    import os
    from utils import send_reset_email
    brevo_key = os.getenv('BREVO_API_KEY', '')
    if not brevo_key:
        return f"<h2>Email Send Test</h2><p>❌ BREVO_API_KEY not configured in environment variables</p>"

    try:
        test_link = "https://digital-queue-management-system-1.onrender.com/"
        result = send_reset_email('teltumdesahil441@gmail.com', test_link, 'Test')
        return f"<h2>Email Send Test</h2><p>Result: {'SUCCESS ✅' if result else 'FAILED ❌'}</p><p>Check Render logs and your email inbox</p>"
    except Exception as e:
        return f"<h2>Email Send Test</h2><p>ERROR: {str(e)}</p><p>Check Render logs for full traceback</p>"


@main_bp.route('/test-ors-api')
def test_ors_api():
    """Test endpoint to verify OpenRouteService API with traffic adjustment"""
    import os
    from utils import calculate_travel_time, get_ist_now_aware, get_traffic_multiplier
    ors_key = os.getenv('OPENROUTESERVICE_API_KEY', '')
    if not ors_key:
        return f"<h2>ORS API Test</h2><p>❌ OPENROUTESERVICE_API_KEY not configured</p>"

    try:
        user_lat, user_lon = 21.110168, 79.087917
        center_lat, center_lon = 20.9125252, 79.1210646

        travel_time = calculate_travel_time(user_lat, user_lon, center_lat, center_lon)

        if travel_time:
            current_time = get_ist_now_aware()
            multiplier = get_traffic_multiplier()
            base_time = round(travel_time / multiplier)

            return f"""
            <h2>ORS API Test + Traffic Adjustment</h2>
            <p>✅ <strong>SUCCESS!</strong></p>
            <p><strong>Current Time:</strong> {current_time.strftime('%I:%M %p')} (Hour: {current_time.hour})</p>
            <p><strong>Base Time (ORS):</strong> ~{base_time} minutes</p>
            <p><strong>Traffic Multiplier:</strong> {multiplier}x</p>
            <p><strong>Adjusted Time:</strong> {travel_time} minutes</p>
            <hr>
            <p><strong>Traffic Periods:</strong></p>
            <ul>
                <li>Peak (9-11 AM, 4-8 PM): ×2.0</li>
                <li>Normal (11 AM-4 PM, 8-10 PM): ×1.8</li>
                <li>Night (10 PM-6 AM): ×1.5</li>
            </ul>
            """
        else:
            return f"<h2>ORS API Test</h2><p>❌ FAILED - Check logs</p>"
    except Exception as e:
        return f"<h2>ORS API Test</h2><p>❌ ERROR: {str(e)}</p>"
