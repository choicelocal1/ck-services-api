from app import db, User, app

with app.app_context():
    admin = User.query.filter_by(username='admin').first()
    if admin:
        db.session.delete(admin)
        db.session.commit()
        print("Admin user deleted.")
    else:
        print("Admin user not found.")
