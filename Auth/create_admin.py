import sys
from app import app
from extensions import db
from models import User

def promote_user(email):
    with app.app_context():
        db.create_all()
        user = User.query.filter_by(email=email).first()
        if not user:
            print(f"Creating new Admin user for {email}...")
            user = User(email=email, name=email.split('@')[0], role='admin')
            db.session.add(user)
        else:
            print(f"Promoting existing user {email} to Admin...")
            user.role = 'admin'
        
        db.session.commit()
        print(f"Success! {email} is now an admin.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python create_admin.py <email_address>")
        sys.exit(1)
        
    promote_user(sys.argv[1])
