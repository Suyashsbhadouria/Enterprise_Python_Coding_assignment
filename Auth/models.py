from .extensions import db
from datetime import datetime

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    name = db.Column(db.String(120), nullable=True)
    profile_pic = db.Column(db.String(255), nullable=True)
    
    # Simple RBAC: 'admin' or 'user'
    role = db.Column(db.String(50), nullable=False, default='user')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def is_admin(self):
        return self.role == 'admin'

    def __repr__(self):
        return f'<User {self.email} ({self.role})>'
