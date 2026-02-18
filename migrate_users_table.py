"""Migration script to add missing columns to users table"""
import os
from sqlalchemy import create_engine, text

# Get database URL from environment
database_url = os.getenv('DATABASE_URL', 'sqlite:///database.db')
if database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql://', 1)

engine = create_engine(database_url)

with engine.connect() as conn:
    # Add address column
    try:
        conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS address VARCHAR(200)"))
        conn.commit()
        print("✅ Added address column")
    except Exception as e:
        print(f"⚠️ address: {e}")
    
    # Add latitude column
    try:
        conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS latitude FLOAT"))
        conn.commit()
        print("✅ Added latitude column")
    except Exception as e:
        print(f"⚠️ latitude: {e}")
    
    # Add longitude column
    try:
        conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS longitude FLOAT"))
        conn.commit()
        print("✅ Added longitude column")
    except Exception as e:
        print(f"⚠️ longitude: {e}")

print("✅ Migration complete")
