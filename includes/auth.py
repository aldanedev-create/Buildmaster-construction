import hashlib
import secrets
import re
import hmac
from datetime import datetime, timedelta
try:
    from werkzeug.security import generate_password_hash, check_password_hash
except ImportError:
    generate_password_hash = None
    check_password_hash = None
from includes.db import query_one, query_all, execute
from includes.functions import log_activity, get_client_ip, get_user_agent

def hash_password(password):
    """Hash password using werkzeug"""
    if generate_password_hash:
        return generate_password_hash(password, method='pbkdf2:sha256')
    salt = secrets.token_hex(8)
    iterations = 600000
    digest = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), iterations).hex()
    return f'pbkdf2:sha256:{iterations}${salt}${digest}'

def verify_password(password, password_hash):
    """Verify password against hash"""
    if check_password_hash:
        return check_password_hash(password_hash, password)
    try:
        method, salt, expected = password_hash.split('$', 2)
        _, algorithm, iterations = method.split(':')
        digest = hashlib.pbkdf2_hmac(algorithm, password.encode(), salt.encode(), int(iterations)).hex()
        return hmac.compare_digest(digest, expected)
    except Exception:
        return False

def validate_password(password):
    """Validate password strength"""
    if len(password) < 8:
        return False, "Password must be at least 8 characters"
    if not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter"
    if not re.search(r"[a-z]", password):
        return False, "Password must contain at least one lowercase letter"
    if not re.search(r"\d", password):
        return False, "Password must contain at least one number"
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        return False, "Password must contain at least one special character"
    return True, "Valid"

def validate_email(email):
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def register_user(name, email, phone, password):
    """Register a new user"""
    # Validate inputs
    if not name or not email or not phone or not password:
        return False, "All fields are required"
    
    if not validate_email(email):
        return False, "Invalid email format"
    
    valid, msg = validate_password(password)
    if not valid:
        return False, msg
    
    # Check if email already exists
    existing = query_one("SELECT user_id FROM users WHERE email = ? AND account_status != 'Deleted'", [email])
    if existing:
        return False, "Email already registered"
    
    # Check for soft-deleted account to restore
    soft_deleted = query_one("SELECT user_id FROM users WHERE email = ? AND account_status = 'Deleted'", [email])
    if soft_deleted:
        # Restore account
        password_hash = hash_password(password)
        execute("""
            UPDATE users 
            SET name = ?, phone = ?, password_hash = ?, account_status = 'Active', 
                deleted_at = NULL, updated_at = CURRENT_TIMESTAMP
            WHERE email = ?
        """, [name, phone, password_hash, email])
        return True, "Account restored successfully"
    
    # Create new account
    password_hash = hash_password(password)
    user_id = execute("""
        INSERT INTO users (name, email, phone, password_hash, role, account_status)
        VALUES (?, ?, ?, ?, 'Customer', 'Active')
    """, [name, email, phone, password_hash])
    
    return True, "Registration successful"

def login_user(email, password, request):
    """Authenticate user and start session"""
    user = query_one("""
        SELECT user_id, name, email, phone, password_hash, role, account_status, 
               two_factor_enabled, two_factor_secret
        FROM users 
        WHERE email = ? AND account_status != 'Deleted'
    """, [email])
    
    if not user:
        return False, "Invalid email or password", None
    
    if user['account_status'] == 'Suspended':
        return False, "Account has been suspended. Contact administrator.", None
    
    if not verify_password(password, user['password_hash']):
        log_activity(user['user_id'], 'Failed Login', 'Invalid password', request)
        return False, "Invalid email or password", None
    
    # Update last login
    execute("UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE user_id = ?", [user['user_id']])
    log_activity(user['user_id'], 'Login', 'User logged in successfully', request)
    
    # Check if 2FA is enabled
    if user['two_factor_enabled']:
        return True, "2FA Required", user
    
    # No 2FA, return user data
    return True, "Login successful", user

def generate_reset_token(email):
    """Generate password reset token"""
    token = secrets.token_urlsafe(32)
    expiry = datetime.now() + timedelta(hours=24)
    
    execute("""
        UPDATE users 
        SET reset_token = ?, reset_token_expiry = ?
        WHERE email = ?
    """, [token, expiry, email])
    
    return token

def verify_reset_token(token):
    """Verify reset token and return user"""
    user = query_one("""
        SELECT user_id, email FROM users 
        WHERE reset_token = ? AND reset_token_expiry > CURRENT_TIMESTAMP
    """, [token])
    return user

def reset_password(token, new_password):
    """Reset password using token"""
    valid, msg = validate_password(new_password)
    if not valid:
        return False, msg
    
    user = verify_reset_token(token)
    if not user:
        return False, "Invalid or expired token"
    
    password_hash = hash_password(new_password)
    execute("""
        UPDATE users 
        SET password_hash = ?, reset_token = NULL, reset_token_expiry = NULL
        WHERE user_id = ?
    """, [password_hash, user['user_id']])
    
    return True, "Password reset successful"

def soft_delete_account(user_id, request):
    """Soft delete user account"""
    execute("""
        UPDATE users 
        SET account_status = 'Deleted', deleted_at = CURRENT_TIMESTAMP
        WHERE user_id = ?
    """, [user_id])
    log_activity(user_id, 'Account Deleted', 'User account soft deleted', request)

def restore_account(email):
    """Restore soft-deleted account on login"""
    user = query_one("SELECT user_id FROM users WHERE email = ? AND account_status = 'Deleted'", [email])
    if user:
        execute("""
            UPDATE users 
            SET account_status = 'Active', deleted_at = NULL
            WHERE user_id = ?
        """, [user['user_id']])
        return True
    return False

def permanently_delete_old_accounts():
    """Delete accounts that have been soft-deleted for more than 30 days"""
    from config.config import Config
    old_deleted = query_all("""
        SELECT user_id FROM users
        WHERE account_status = 'Deleted'
        AND deleted_at <= datetime('now', '-' || ? || ' days')
    """, [Config.SOFT_DELETE_DAYS])

    for user in old_deleted:
        user_id = user['user_id']
        project_ids = query_all("SELECT project_id FROM projects WHERE customer_id = ?", [user_id])
        for project in project_ids:
            execute("DELETE FROM payments WHERE project_id = ?", [project['project_id']])
            execute("DELETE FROM project_updates WHERE project_id = ?", [project['project_id']])
        execute("DELETE FROM projects WHERE customer_id = ?", [user_id])
        execute("DELETE FROM two_fa_codes WHERE user_id = ?", [user_id])
        execute("DELETE FROM activity_logs WHERE user_id = ?", [user_id])
        execute("DELETE FROM security_alerts WHERE user_id = ?", [user_id])

    execute("""
        DELETE FROM users 
        WHERE account_status = 'Deleted' 
        AND deleted_at <= datetime('now', '-' || ? || ' days')
    """, [Config.SOFT_DELETE_DAYS])

def require_role(required_roles):
    """Decorator for role-based access control"""
    from functools import wraps
    from flask import session, redirect, url_for, flash
    
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                flash('Please login to access this page', 'warning')
                return redirect(url_for('login'))
            
            if session.get('role') not in required_roles:
                flash('You do not have permission to access this page', 'danger')
                return redirect(url_for('index'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator
