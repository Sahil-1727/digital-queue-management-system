from app import app, db, init_db

if __name__ == '__main__':
    with app.app_context():
        db.drop_all()
        db.create_all()
        init_db()
        print("✅ Database created successfully with is_walkin column")
