from app import app, db, User

def create_user(username, password):
    with app.app_context():
        # Check if user already exists
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            print(f"User '{username}' already exists. Updating password.")
            existing_user.set_password(password)
        else:
            # Create new user
            new_user = User(username=username)
            new_user.set_password(password)
            db.session.add(new_user)
        
        # Commit changes
        db.session.commit()
        print(f"User '{username}' created/updated successfully.")

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 3:
        print("Usage: python create_user.py <username> <password>")
    else:
        create_user(sys.argv[1], sys.argv[2])
