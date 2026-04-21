from flask import Blueprint, redirect, url_for, session, current_app, request, abort
from functools import wraps
from extensions import oauth, db
from models import User

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Allow if running without app context or session isn't loaded (fallback)
        if 'user_id' not in session:
            abort(403)
        user = db.session.get(User, session['user_id'])
        if not user or not user.is_admin():
            abort(403) # Forbidden
        return f(*args, **kwargs)
    return decorated_function

@auth_bp.route('/login')
def login():
    # Redirect to Google auth
    redirect_uri = url_for('auth.auth_callback', _external=True)
    return oauth.google.authorize_redirect(redirect_uri)

@auth_bp.route('/callback')
def auth_callback():
    token = oauth.google.authorize_access_token()
    user_info = token.get('userinfo')
    
    if user_info:
        email = user_info.get('email')
        name = user_info.get('name')
        picture = user_info.get('picture')
        
        # Check if user exists
        user = User.query.filter_by(email=email).first()
        if not user:
            # Create a new standard user by default
            user = User(email=email, name=name, profile_pic=picture)
            db.session.add(user)
            db.session.commit()
            
        session['user_id'] = user.id
        session['user_email'] = user.email
        session['user_role'] = user.role
        
    return redirect(url_for('overview'))

@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('public_login_page'))
