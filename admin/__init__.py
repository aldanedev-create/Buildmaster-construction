from flask import Blueprint

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

from admin import activity_logs, backup, dashboard, manage_admins, manage_customers
from admin import manage_gallery, manage_projects, manage_services, reports, siem
