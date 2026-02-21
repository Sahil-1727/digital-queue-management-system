#!/usr/bin/env python3
"""
Template Cleanup Script
Removes inline styles and hardcoded colors from all HTML templates
"""

import os
import re
from pathlib import Path

TEMPLATES_DIR = Path("/Users/sahilteltumde/Desktop/QueueFlow/templates")

# Patterns to remove or replace
PATTERNS = [
    # Remove data-theme attributes
    (r'\s*data-theme="[^"]*"', ''),
    
    # Remove inline style attributes with hardcoded colors
    (r'\s*style="[^"]*(?:background|color|border-color):\s*(?:#[0-9a-fA-F]{3,6}|rgb[a]?\([^)]+\))[^"]*"', ''),
    
    # Replace common inline styles with CSS variables
    (r'style="background:\s*var\(--bg-primary\)', 'style="background: var(--bg-main)'),
    (r'style="background:\s*var\(--bg-secondary\)', 'style="background: var(--bg-soft)'),
    (r'style="color:\s*var\(--primary-color\)', 'style="color: var(--color-primary)'),
    (r'--primary-color', '--color-primary'),
    (r'--primary-dark', '--color-primary-dark'),
    (r'--bg-tertiary', '--bg-soft'),
    (r'--card-bg', '--bg-card'),
    (r'--border\b', '--border-light'),
    (r'--text-muted', '--text-muted'),
    (r'--radius-md', '--radius-md'),
    (r'--shadow-2xl', '--shadow-xl'),
    
    # Remove theme-switcher.js references
    (r'\s*<script src="[^"]*theme-switcher\.js[^"]*"></script>', ''),
    (r'\s*<script src="[^"]*dark-mode\.js[^"]*"></script>', ''),
    (r'\s*<script src="[^"]*theme-toggle\.js[^"]*"></script>', ''),
]

def clean_template(filepath):
    """Clean a single template file"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Apply all patterns
        for pattern, replacement in PATTERNS:
            content = re.sub(pattern, replacement, content)
        
        # Only write if changes were made
        if content != original_content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        return False
    except Exception as e:
        print(f"Error processing {filepath}: {e}")
        return False

def main():
    """Process all templates"""
    print("🧹 Cleaning templates...")
    print(f"📁 Directory: {TEMPLATES_DIR}")
    
    cleaned_count = 0
    total_count = 0
    
    for filepath in TEMPLATES_DIR.rglob("*.html"):
        total_count += 1
        if clean_template(filepath):
            cleaned_count += 1
            print(f"✓ Cleaned: {filepath.name}")
    
    print(f"\n✅ Complete! Cleaned {cleaned_count}/{total_count} templates")

if __name__ == "__main__":
    main()
