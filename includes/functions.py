import os
import uuid
import secrets
import html
import re
from datetime import datetime
from flask import request, session
from werkzeug.utils import secure_filename
from config.config import Config
from includes.db import execute

def get_client_ip():
    """Get client IP address"""
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0]
    return request.remote_addr

def get_user_agent():
    """Get user agent string"""
    return request.headers.get('User-Agent', 'Unknown')

def log_activity(user_id, action, details, request_obj=None):
    """Log user activity"""
    ip = get_client_ip() if request_obj else 'System'
    user_agent = get_user_agent() if request_obj else 'System'
    
    # Get user email
    from includes.db import query_one
    user = query_one("SELECT email FROM users WHERE user_id = ?", [user_id]) if user_id else None
    
    execute("""
        INSERT INTO activity_logs (user_id, user_email, action, details, ip_address, user_agent)
        VALUES (?, ?, ?, ?, ?, ?)
    """, [user_id, user['email'] if user else None, action, details, ip, user_agent])

def allowed_file(filename):
    """Check if file type is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_EXTENSIONS

def upload_file(file, folder):
    """Upload file and return path"""
    if not file or file.filename == '':
        return None
    
    if not allowed_file(file.filename):
        return None
    
    filename = secure_filename(file.filename)
    unique_filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}_{filename}"
    
    upload_path = os.path.join(Config.UPLOAD_FOLDER, folder)
    os.makedirs(upload_path, exist_ok=True)
    
    file_path = os.path.join(upload_path, unique_filename)
    file.save(file_path)
    
    return f"uploads/{folder}/{unique_filename}"

def generate_csrf_token():
    """Generate CSRF token"""
    if 'csrf_token' not in session:
        session['csrf_token'] = secrets.token_hex(32)
    return session['csrf_token']

def verify_csrf_token(token):
    """Verify CSRF token"""
    return token == session.get('csrf_token')

def send_whatsapp_notification(phone, message):
    """Send WhatsApp notification (simplified)"""
    if not Config.WHATSAPP_ENABLED:
        return None
    phone = ''.join(ch for ch in (phone or Config.WHATSAPP_BUSINESS_NUMBER) if ch.isdigit())
    encoded_msg = message.replace(' ', '%20')
    return f"https://wa.me/{phone}?text={encoded_msg}"

def build_whatsapp_link(message, phone=None):
    return send_whatsapp_notification(phone or Config.WHATSAPP_BUSINESS_NUMBER, message)

def send_email(to_email, subject, body):
    """Send email through configured SMTP/Gmail settings."""
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    
    try:
        if not Config.SMTP_USERNAME or not Config.SMTP_PASSWORD:
            print("Email skipped: SMTP_USERNAME/SMTP_PASSWORD are not configured")
            return False

        msg = MIMEMultipart()
        msg['From'] = Config.FROM_EMAIL or Config.SMTP_USERNAME
        msg['To'] = to_email
        msg['Subject'] = subject
        
        msg.attach(MIMEText(body, 'html'))
        
        server = smtplib.SMTP(Config.SMTP_SERVER, Config.SMTP_PORT)
        if Config.SMTP_USE_TLS:
            server.starttls()
        server.login(Config.SMTP_USERNAME, Config.SMTP_PASSWORD)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"Email error: {e}")
        return False

def validate_email(email):
    return re.match(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$", email or "") is not None

def sanitize_input(value):
    return html.escape((value or "").strip())
