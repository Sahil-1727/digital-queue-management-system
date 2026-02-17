#!/usr/bin/env python3
"""
Reset database and add demo data
Run this script to start fresh with demo users and queue
"""
import os
import sys

# Remove existing database first
db_path = 'database.db'
if os.path.exists(db_path):
    os.remove(db_path)
    print(f"✓ Removed existing database: {db_path}")

# Now import and initialize
from app import app, db, User, ServiceCenter, Admin, Token, generate_password_hash
from datetime import datetime, timedelta

with app.app_context():
    # Create all tables
    db.create_all()
    
    # Add service centers
    centers = [
        ServiceCenter(name='City Clinic 1', category='Medical', location='Sitabuldi, Nagpur', avg_service_time=20),
        ServiceCenter(name='City Clinic 2', category='Medical', location='Dharampeth, Nagpur', avg_service_time=18),
        ServiceCenter(name='Mobile Service Center 1', category='Electronics', location='Sadar, Nagpur', avg_service_time=25),
        ServiceCenter(name='Mobile Service Center 2', category='Electronics', location='Wardha Road, Nagpur', avg_service_time=22),
    ]
    db.session.add_all(centers)
    db.session.commit()
    
    # Add admins
    admins = [
        Admin(username='admin1', password=generate_password_hash('admin123'), service_center_id=1),
        Admin(username='admin2', password=generate_password_hash('admin123'), service_center_id=2),
        Admin(username='admin3', password=generate_password_hash('admin123'), service_center_id=3),
        Admin(username='admin4', password=generate_password_hash('admin123'), service_center_id=4),
    ]
    db.session.add_all(admins)
    db.session.commit()
    
    # Add demo users
    demo_users = [
        User(name='Rahul Sharma', mobile='9876543210', password=generate_password_hash('demo123')),
        User(name='Priya Patel', mobile='9876543211', password=generate_password_hash('demo123')),
        User(name='Amit Kumar', mobile='9876543212', password=generate_password_hash('demo123')),
        User(name='Sneha Deshmukh', mobile='9876543213', password=generate_password_hash('demo123')),
        User(name='Vikram Singh', mobile='9876543214', password=generate_password_hash('demo123')),
        User(name='Anjali Mehta', mobile='9876543215', password=generate_password_hash('demo123')),
        User(name='Rohan Gupta', mobile='9876543216', password=generate_password_hash('demo123')),
        User(name='Pooja Joshi', mobile='9876543217', password=generate_password_hash('demo123')),
        User(name='Karan Verma', mobile='9876543218', password=generate_password_hash('demo123')),
        User(name='Neha Reddy', mobile='9876543219', password=generate_password_hash('demo123')),
    ]
    db.session.add_all(demo_users)
    db.session.commit()
    
    # Create demo tokens for City Clinic 1
    now = datetime.now()
    demo_tokens = [
        Token(user_id=1, service_center_id=1, token_number='T001', status='Serving', created_time=now - timedelta(minutes=60)),
        Token(user_id=2, service_center_id=1, token_number='T002', status='Active', created_time=now - timedelta(minutes=55)),
        Token(user_id=3, service_center_id=1, token_number='T003', status='Active', created_time=now - timedelta(minutes=50)),
        Token(user_id=4, service_center_id=1, token_number='T004', status='Active', created_time=now - timedelta(minutes=45)),
        Token(user_id=5, service_center_id=1, token_number='T005', status='Active', created_time=now - timedelta(minutes=40)),
        Token(user_id=6, service_center_id=1, token_number='T006', status='Active', created_time=now - timedelta(minutes=35)),
        Token(user_id=7, service_center_id=1, token_number='T007', status='Active', created_time=now - timedelta(minutes=30)),
        Token(user_id=8, service_center_id=1, token_number='T008', status='Active', created_time=now - timedelta(minutes=25)),
        Token(user_id=9, service_center_id=1, token_number='T009', status='Active', created_time=now - timedelta(minutes=20)),
        Token(user_id=10, service_center_id=1, token_number='T010', status='Active', created_time=now - timedelta(minutes=15)),
    ]
    db.session.add_all(demo_tokens)
    db.session.commit()

print("✓ Created new database with demo data")
print("\n" + "="*60)
print("DEMO DATA CREATED SUCCESSFULLY!")
print("="*60)
print("\n📋 Demo Users (10 users):")
print("   Mobile: 9876543210-9876543219")
print("   Password: demo123")
print("\n🎫 Demo Queue (City Clinic 1):")
print("   - 1 token currently being served (T001)")
print("   - 9 tokens waiting in queue (T002-T010)")
print("\n👨💼 Admin Accounts:")
print("   Username: admin1, admin2, admin3, admin4")
print("   Password: admin123")
print("\n🚀 Start the app with: python app.py")
print("="*60 + "\n")
