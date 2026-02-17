import sqlite3
import os

# Path to database
db_path = 'instance/database.db'

if os.path.exists(db_path):
    print(f"Found database at {db_path}")
    
    # Connect to database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check if password column exists
    cursor.execute("PRAGMA table_info(service_center_registrations)")
    columns = [row[1] for row in cursor.fetchall()]
    
    if 'password' not in columns:
        print("Adding password column...")
        cursor.execute("ALTER TABLE service_center_registrations ADD COLUMN password TEXT NOT NULL DEFAULT ''")
        conn.commit()
        print("✅ Password column added successfully")
    else:
        print("✅ Password column already exists")
    
    conn.close()
else:
    print(f"❌ Database not found at {db_path}")
    print("Run the app first to create the database")
