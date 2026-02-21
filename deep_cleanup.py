#!/usr/bin/env python3
"""
COMPLETE Template Cleanup Script
Removes ALL hardcoded colors, inline styles, and ensures 100% centralization
"""

import os
import re
from pathlib import Path

TEMPLATES_DIR = Path("/Users/sahilteltumde/Desktop/QueueFlow/templates")

def clean_template(filepath):
    """Aggressively clean template of all hardcoded styling"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original = content
        
        # Remove inline background with hex colors
        content = re.sub(r'style="[^"]*background:\s*#[0-9a-fA-F]{3,6}[^"]*"', '', content)
        content = re.sub(r'style="[^"]*background:\s*linear-gradient\([^)]*#[0-9a-fA-F]{3,6}[^)]*\)[^"]*"', '', content)
        
        # Remove inline color with hex
        content = re.sub(r'style="[^"]*color:\s*#[0-9a-fA-F]{3,6}[^"]*"', '', content)
        
        # Remove inline border-color with hex
        content = re.sub(r'style="[^"]*border-color:\s*#[0-9a-fA-F]{3,6}[^"]*"', '', content)
        
        # Remove style blocks with hardcoded colors in templates
        content = re.sub(r'<style>[^<]*#[0-9a-fA-F]{3,6}[^<]*</style>', '', content, flags=re.DOTALL)
        
        # Replace common hardcoded inline backgrounds
        content = content.replace('background: #F8FAFC', 'background: var(--bg-main)')
        content = content.replace('background: #f8f9fa', 'background: var(--bg-soft)')
        content = content.replace('background: #0F172A', 'background: var(--color-primary)')
        content = content.replace('color: #0F172A', 'color: var(--text-primary)')
        
        # Remove data-theme attributes
        content = re.sub(r'\s*data-theme="[^"]*"', '', content)
        
        # Remove prefers-color-scheme media queries
        content = re.sub(r'@media\s*\(prefers-color-scheme:\s*dark\)[^}]*\{[^}]*\}', '', content, flags=re.DOTALL)
        
        # Clean up double spaces
        content = re.sub(r'  +', ' ', content)
        
        if content != original:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        return False
    except Exception as e:
        print(f"Error: {filepath}: {e}")
        return False

def main():
    print("🧹 COMPLETE TEMPLATE CLEANUP")
    print("=" * 60)
    
    cleaned = 0
    total = 0
    
    for filepath in TEMPLATES_DIR.rglob("*.html"):
        total += 1
        if clean_template(filepath):
            cleaned += 1
            print(f"✓ {filepath.name}")
    
    print("=" * 60)
    print(f"✅ Cleaned {cleaned}/{total} templates")

if __name__ == "__main__":
    main()
