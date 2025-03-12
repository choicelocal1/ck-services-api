from app import db, User, app

with app.app_context():
    db.create_all()
    
    # Create admin user if it doesn't exist
    if not User.query.filter_by(username='admin').first():
        user = User(username='admin')
        user.set_password('dveThESOlANg')  # Make sure to change this password
        db.session.add(user)
        db.session.commit()
        print("Admin user created.")
    else:
        print("Admin user already exists.")
