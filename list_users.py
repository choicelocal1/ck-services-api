# list_users.py
from app import app, db, User

def list_users():
    with app.app_context():
        users = User.query.all()
        
        if not users:
            print("No users found in the database.")
            return
        
        print("\nUsers in the database:")
        print("=" * 70)
        print(f"{'ID':<5} {'Username':<20} {'Password Hash (first 20 chars)':<40}")
        print("-" * 70)
        
        for user in users:
            # Only show first 20 characters of the hash for security
            hash_preview = user.password_hash[:20] + "..." if user.password_hash else "None"
            print(f"{user.id:<5} {user.username:<20} {hash_preview:<40}")
        
        print("=" * 70)
        print(f"Total users: {len(users)}")
        print("\nNote: For security, only showing partial password hashes")

if __name__ == "__main__":
    list_users()
