#!/usr/bin/env python3
"""
Batch update all remaining QueueFlow templates with premium UI pattern
"""

import os
import re

TEMPLATES_DIR = '/Users/sahilteltumde/Desktop/QueueFlow/templates'

# Standard header replacement
HEADER_OLD_PATTERNS = [
    r'<link rel="stylesheet" href="{{ url_for\(\'static\', filename=\'css/theme\.css\'\) }}">',
    r'<link rel="stylesheet" href="{{ url_for\(\'static\', filename=\'css/custom\.css\'\) }}">',
]

HEADER_NEW = '''<link rel="stylesheet" href="{{ url_for('static', filename='css/premium.css') }}">'''

# Standard footer additions
FOOTER_ADDITION = '''<script src="{{ url_for('static', filename='js/premium-animations.js') }}"></script>'''

# Body class addition
BODY_OLD = r'<body([^>]*)>'
BODY_NEW = r'<body\1 class="page-content">' if 'class=' not in r'\1' else r'<body\1>'

# Color replacements
COLOR_REPLACEMENTS = {
    '#2DD4BF': 'var(--primary-color)',
    '#14B8A6': 'var(--primary-dark)',
    'rgba(45, 212, 191,': 'rgba(79, 70, 229,',
}

# Badge class replacements
BADGE_REPLACEMENTS = {
    'bg-primary': 'badge-primary',
    'bg-success': 'badge-success',
    'bg-warning': 'badge-warning',
    'bg-danger': 'badge-danger',
    'bg-info': 'badge-info',
}

def update_template(filepath):
    """Update a single template file"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original = content
    
    # Remove old CSS links
    for pattern in HEADER_OLD_PATTERNS:
        content = re.sub(pattern, '', content)
    
    # Add premium.css if not present
    if 'premium.css' not in content:
        content = content.replace(
            '<link rel="stylesheet" href="{{ url_for(\'static\', filename=\'css/bootstrap.min.css\') }}">',
            '<link rel="stylesheet" href="{{ url_for(\'static\', filename=\'css/bootstrap.min.css\') }}">\n    ' + HEADER_NEW
        )
    
    # Add premium-animations.js if not present
    if 'premium-animations.js' not in content:
        content = content.replace(
            '<script src="{{ url_for(\'static\', filename=\'js/bootstrap.bundle.min.js\') }}"></script>',
            '<script src="{{ url_for(\'static\', filename=\'js/bootstrap.bundle.min.js\') }}"></script>\n    ' + FOOTER_ADDITION
        )
    
    # Update body class
    if 'page-content' not in content:
        content = re.sub(r'<body([^>]*)>', lambda m: f'<body{m.group(1)} class="page-content">' if 'class=' not in m.group(1) else m.group(0), content)
    
    # Replace colors
    for old_color, new_color in COLOR_REPLACEMENTS.items():
        content = content.replace(old_color, new_color)
    
    # Replace badge classes
    for old_badge, new_badge in BADGE_REPLACEMENTS.items():
        content = re.sub(rf'\bclass="([^"]*){old_badge}([^"]*)"', rf'class="\1{new_badge}\2"', content)
    
    # Update theme toggle button if present
    if 'theme-toggle' in content and 'var(--primary-color)' not in content:
        content = re.sub(
            r'background: linear-gradient\(135deg, #2DD4BF, #14B8A6\)',
            'background: linear-gradient(135deg, var(--primary-color), var(--primary-dark))',
            content
        )
    
    # Add hover-lift and fade-in-up to cards if not present
    content = re.sub(
        r'<div class="card"([^>]*)>',
        lambda m: f'<div class="card hover-lift fade-in-up"{m.group(1)}>' if 'hover-lift' not in m.group(0) else m.group(0),
        content
    )
    
    # Only write if changed
    if content != original:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    return False

def main():
    """Main execution"""
    templates_to_update = [
        'forgot_password.html',
        'reset_password.html',
        'admin_forgot_password.html',
        'admin_reset_password.html',
        'superadmin_login.html',
        'registration_payment.html',
        'service_detail.html',
        'register_center.html',
        'register_center_success.html',
        'track_status.html',
        'track_token.html',
        'token_qr.html',
        'user_history.html',
        'admin_history.html',
        'admin_profile.html',
        'admin_analytics.html',
        'add_walkin.html',
        'no_show_form.html',
        'owner_dashboard.html',
        'superadmin_dashboard.html',
        'superadmin_admins.html',
        'superadmin_edit_admin.html',
        'superadmin_manage_centers.html',
    ]
    
    updated = 0
    for template in templates_to_update:
        filepath = os.path.join(TEMPLATES_DIR, template)
        if os.path.exists(filepath):
            if update_template(filepath):
                print(f'✅ Updated: {template}')
                updated += 1
            else:
                print(f'⏭️  Skipped (no changes): {template}')
        else:
            print(f'❌ Not found: {template}')
    
    print(f'\n🎉 Updated {updated} templates!')

if __name__ == '__main__':
    main()
