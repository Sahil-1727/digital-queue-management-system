#!/usr/bin/env python3
"""
Batch update all templates to use centralized theme system
Replaces premium.css and dark-mode.css with theme.css
"""

import os
import re

TEMPLATES_DIR = "templates"

def update_template(filepath):
    """Update a single template file"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original = content
    
    # Replace data-theme="dark" with data-theme="midnight"
    content = content.replace('data-theme="dark"', 'data-theme="midnight"')
    
    # Replace CSS links
    content = re.sub(
        r'<link rel="stylesheet" href="\{\{ url_for\(\'static\', filename=\'css/premium\.css\'\) \}\}">',
        '',
        content
    )
    content = re.sub(
        r'<link rel="stylesheet" href="\{\{ url_for\(\'static\', filename=\'css/dark-mode\.css\'\) \}\}">',
        '',
        content
    )
    
    # Add theme.css after bootstrap.min.css
    content = re.sub(
        r'(<link rel="stylesheet" href="\{\{ url_for\(\'static\', filename=\'css/bootstrap\.min\.css\'\) \}\}">)',
        r'\1\n    <link rel="stylesheet" href="{{ url_for(\'static\', filename=\'css/theme.css\') }}">',
        content
    )
    
    # Remove dark-mode.js script
    content = re.sub(
        r'<script src="\{\{ url_for\(\'static\', filename=\'js/dark-mode\.js\'\) \}\}"></script>\n\s*',
        '',
        content
    )
    
    # Replace premium-animations.js with theme-switcher.js
    content = re.sub(
        r'<script src="\{\{ url_for\(\'static\', filename=\'js/premium-animations\.js\'\) \}\}"></script>',
        '<script src="{{ url_for(\'static\', filename=\'js/theme-switcher.js\') }}"></script>',
        content
    )
    
    # Remove theme-toggle.js (functionality now in theme-switcher.js)
    content = re.sub(
        r'<script src="\{\{ url_for\(\'static\', filename=\'js/theme-toggle\.js\'\) \}\}"></script>\n\s*',
        '',
        content
    )
    
    # Update inline styles to use CSS variables
    # Replace hardcoded colors with variables
    replacements = {
        '#2DD4BF': 'var(--color-primary)',
        '#14B8A6': 'var(--color-primary-dark)',
        '#4F46E5': 'var(--color-primary)',
        '#4338CA': 'var(--color-primary-dark)',
        'rgba(45, 212, 191,': 'rgba(15, 76, 92,',
        'rgba(79, 70, 229,': 'rgba(15, 76, 92,',
    }
    
    for old, new in replacements.items():
        content = content.replace(old, new)
    
    # Update theme toggle button to use CSS variables
    content = re.sub(
        r'background: linear-gradient\(135deg, var\(--primary-color\), var\(--primary-dark\)\)',
        'background: var(--color-primary)',
        content
    )
    
    # Only write if changed
    if content != original:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    return False

def main():
    """Update all templates"""
    updated = 0
    skipped = 0
    
    for filename in os.listdir(TEMPLATES_DIR):
        if filename.endswith('.html'):
            filepath = os.path.join(TEMPLATES_DIR, filename)
            if update_template(filepath):
                print(f"✅ Updated: {filename}")
                updated += 1
            else:
                print(f"⏭️  Skipped: {filename} (no changes)")
                skipped += 1
    
    print(f"\n📊 Summary:")
    print(f"   Updated: {updated}")
    print(f"   Skipped: {skipped}")
    print(f"   Total: {updated + skipped}")

if __name__ == "__main__":
    main()
