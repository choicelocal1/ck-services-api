# init_db.py
from app import db, User, app

with app.app_context():
    # Drop all tables
    db.drop_all()
    
    # Create all tables
    db.create_all()
    
    # Create admin user
    user = User(username='admin')
    user.set_password('changeme')  # Make sure to change this password
    db.session.add(user)
    
    try:
        db.session.commit()
        print("Database initialized successfully.")
        print("Admin user created.")
    except Exception as e:
        db.session.rollback()
        print(f"Error: {e}")
