import os
from datetime import timedelta
try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv():
        return False

# Load environment variables from .env file
load_dotenv()

class Config:
    # Flask Configuration
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    DEBUG = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    
    # Session Configuration
    SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', 'False').lower() == 'true'
    SESSION_COOKIE_HTTPONLY = os.environ.get('SESSION_COOKIE_HTTPONLY', 'True').lower() == 'true'
    SESSION_COOKIE_SAMESITE = os.environ.get('SESSION_COOKIE_SAMESITE', 'Lax')
    PERMANENT_SESSION_LIFETIME = timedelta(days=int(os.environ.get('PERMANENT_SESSION_LIFETIME_DAYS', 7)))
    
    # Database
    DATABASE_PATH = os.environ.get('DATABASE_PATH', 'sql/construction.db')
    DATABASE_BACKUP_PATH = os.environ.get('DATABASE_BACKUP_PATH', 'backups')
    SOFT_DELETE_DAYS = int(os.environ.get('SOFT_DELETE_DAYS', 30))
    
    # Security
    PASSWORD_MIN_LENGTH = int(os.environ.get('PASSWORD_MIN_LENGTH', 8))
    TWO_FACTOR_APP_NAME = os.environ.get('TWO_FACTOR_APP_NAME', 'ConstructionWebsite')
    CSRF_ENABLED = os.environ.get('CSRF_ENABLED', 'True').lower() == 'true'
    MAINTENANCE_MODE = os.environ.get('MAINTENANCE_MODE', 'False').lower() == 'true'
    MAINTENANCE_MESSAGE = os.environ.get(
        'MAINTENANCE_MESSAGE',
        'We are making improvements and will be back shortly.'
    )
    
    # Rate Limiting
    RATE_LIMIT_ENABLED = os.environ.get('RATE_LIMIT_ENABLED', 'True').lower() == 'true'
    RATE_LIMIT_REQUESTS = int(os.environ.get('RATE_LIMIT_REQUESTS', 100))
    RATE_LIMIT_PERIOD = int(os.environ.get('RATE_LIMIT_PERIOD', 3600))
    
    # WhatsApp Configuration
    WHATSAPP_ENABLED = os.environ.get('WHATSAPP_ENABLED', 'True').lower() == 'true'
    WHATSAPP_BUSINESS_NUMBER = os.environ.get('WHATSAPP_BUSINESS_NUMBER', '18765550123')
    ADMIN_WHATSAPP_NUMBER = os.environ.get('ADMIN_WHATSAPP_NUMBER', WHATSAPP_BUSINESS_NUMBER)
    WHATSAPP_API_TOKEN = os.environ.get('WHATSAPP_API_TOKEN', '')
    WHATSAPP_API_URL = os.environ.get('WHATSAPP_API_URL', '')
    WHATSAPP_WEBHOOK_SECRET = os.environ.get('WHATSAPP_WEBHOOK_SECRET', '')
    WHATSAPP_PREFILL_TEXT = os.environ.get('WHATSAPP_PREFILL_TEXT', 'Hi, I\'m interested in your construction services')
    
    # Email Configuration
    SMTP_ENABLED = os.environ.get('SMTP_ENABLED', 'False').lower() == 'true'
    SMTP_SERVER = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
    SMTP_PORT = int(os.environ.get('SMTP_PORT', 587))
    SMTP_USERNAME = os.environ.get('SMTP_USERNAME', '')
    SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD', '')
    SMTP_USE_TLS = os.environ.get('SMTP_USE_TLS', 'True').lower() == 'true'
    FROM_EMAIL = os.environ.get('FROM_EMAIL', 'noreply@construction.com')
    FROM_NAME = os.environ.get('FROM_NAME', 'Construction Website')
    ADMIN_ALERT_EMAIL = os.environ.get('ADMIN_ALERT_EMAIL', 'admin@construction.com')
    
    # File Upload
    MAX_CONTENT_LENGTH = int(os.environ.get('MAX_CONTENT_LENGTH', 16 * 1024 * 1024))
    ALLOWED_EXTENSIONS = set(os.environ.get('ALLOWED_EXTENSIONS', 'png,jpg,jpeg,gif,pdf,dwg').split(','))
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', 'uploads')
    MAX_IMAGE_WIDTH = int(os.environ.get('MAX_IMAGE_WIDTH', 2000))
    MAX_IMAGE_HEIGHT = int(os.environ.get('MAX_IMAGE_HEIGHT', 2000))
    
    # Backup Configuration
    BACKUP_ENABLED = os.environ.get('BACKUP_ENABLED', 'True').lower() == 'true'
    BACKUP_AUTO_SCHEDULE = os.environ.get('BACKUP_AUTO_SCHEDULE', 'False').lower() == 'true'
    BACKUP_SCHEDULE_HOUR = int(os.environ.get('BACKUP_SCHEDULE_HOUR', 2))
    BACKUP_SCHEDULE_DAY = int(os.environ.get('BACKUP_SCHEDULE_DAY', 0))
    BACKUP_RETENTION_DAYS = int(os.environ.get('BACKUP_RETENTION_DAYS', 30))
    BACKUP_COMPRESSION_LEVEL = int(os.environ.get('BACKUP_COMPRESSION_LEVEL', 6))
    
    # Payment Gateway
    PAYMENT_ENABLED = os.environ.get('PAYMENT_ENABLED', 'False').lower() == 'true'
    STRIPE_PUBLIC_KEY = os.environ.get('STRIPE_PUBLIC_KEY', '')
    STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY', '')
    PAYPAL_CLIENT_ID = os.environ.get('PAYPAL_CLIENT_ID', '')
    PAYPAL_CLIENT_SECRET = os.environ.get('PAYPAL_CLIENT_SECRET', '')
    PAYPAL_MODE = os.environ.get('PAYPAL_MODE', 'sandbox')
    
    # Google Services
    GOOGLE_MAPS_API_KEY = os.environ.get('GOOGLE_MAPS_API_KEY', '')
    RECAPTCHA_SITE_KEY = os.environ.get('RECAPTCHA_SITE_KEY', '')
    RECAPTCHA_SECRET_KEY = os.environ.get('RECAPTCHA_SECRET_KEY', '')
    RECAPTCHA_ENABLED = os.environ.get('RECAPTCHA_ENABLED', 'False').lower() == 'true'
    
    # Analytics
    GA_TRACKING_ID = os.environ.get('GA_TRACKING_ID', '')
    SENTRY_DSN = os.environ.get('SENTRY_DSN', '')
    
    # Admin Notifications
    ADMIN_EMAILS = [email.strip() for email in os.environ.get('ADMIN_EMAILS', '').split(',') if email.strip()]
    ADMIN_PHONES = [phone.strip() for phone in os.environ.get('ADMIN_PHONES', '').split(',') if phone.strip()]
    ADMIN_WHATSAPP_NUMBER = os.environ.get('ADMIN_WHATSAPP_NUMBER', '')
    
    # System Configuration
    TIMEZONE = os.environ.get('TIMEZONE', 'America/New_York')
    DATE_FORMAT = os.environ.get('DATE_FORMAT', '%Y-%m-%d %H:%M:%S')
    DISPLAY_TIMEZONE = os.environ.get('DISPLAY_TIMEZONE', 'America/New_York')
    MAINTENANCE_MODE = os.environ.get('MAINTENANCE_MODE', 'False').lower() == 'true'
    MAINTENANCE_MESSAGE = os.environ.get('MAINTENANCE_MESSAGE', 'Site is under maintenance. Please check back soon.')
    
    # Logging
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_FILE = os.environ.get('LOG_FILE', 'logs/app.log')
    LOG_MAX_SIZE = int(os.environ.get('LOG_MAX_SIZE', 10 * 1024 * 1024))
    LOG_BACKUP_COUNT = int(os.environ.get('LOG_BACKUP_COUNT', 5))
    LOG_FORMAT = os.environ.get('LOG_FORMAT', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Cache
    CACHE_ENABLED = os.environ.get('CACHE_ENABLED', 'False').lower() == 'true'
    CACHE_TYPE = os.environ.get('CACHE_TYPE', 'simple')
    REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
    CACHE_DEFAULT_TIMEOUT = int(os.environ.get('CACHE_DEFAULT_TIMEOUT', 300))
    
    # API Configuration
    API_ENABLED = os.environ.get('API_ENABLED', 'True').lower() == 'true'
    API_PREFIX = os.environ.get('API_PREFIX', '/api/v1')
    API_RATE_LIMIT = int(os.environ.get('API_RATE_LIMIT', 1000))
    API_RATE_LIMIT_PERIOD = int(os.environ.get('API_RATE_LIMIT_PERIOD', 3600))
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', SECRET_KEY)
    JWT_ACCESS_TOKEN_EXPIRES = int(os.environ.get('JWT_ACCESS_TOKEN_EXPIRES', 3600))
    JWT_REFRESH_TOKEN_EXPIRES = int(os.environ.get('JWT_REFRESH_TOKEN_EXPIRES', 86400))
    
    @classmethod
    def is_production(cls):
        return os.environ.get('FLASK_ENV', 'development') == 'production'
    
    @classmethod
    def get_database_url(cls):
        return f"sqlite:///{cls.DATABASE_PATH}"
