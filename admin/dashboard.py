from flask import flash, redirect, render_template, request, session, url_for
from includes.auth import require_role
from includes.db import query_one, query_all
from includes.functions import log_activity, verify_csrf_token
from includes.settings import get_maintenance_message, is_maintenance_mode, set_setting
from admin import admin_bp

@admin_bp.route('/dashboard')
@require_role(['SuperAdmin', 'ProjectManager'])
def dashboard():
    stats = {}
    
    if session['role'] == 'SuperAdmin':
        stats['total_users'] = query_one("SELECT COUNT(*) as count FROM users WHERE account_status != 'Deleted'")['count']
        stats['total_projects'] = query_one("SELECT COUNT(*) as count FROM projects")['count']
        stats['pending_projects'] = query_one("SELECT COUNT(*) as count FROM projects WHERE status = 'Pending'")['count']
        stats['total_services'] = query_one("SELECT COUNT(*) as count FROM services WHERE is_active = 1")['count']
        stats['completed_projects'] = query_one("SELECT COUNT(*) as count FROM projects WHERE status = 'Completed'")['count']
        stats['total_revenue'] = query_one("SELECT COALESCE(SUM(amount), 0) as total FROM payments WHERE payment_status = 'Completed'")['total']
        stats['recent_activities'] = query_all("SELECT * FROM activity_logs ORDER BY timestamp DESC LIMIT 10")
        stats['recent_projects'] = query_all("""
            SELECT p.*, u.name as customer_name, s.service_name 
            FROM projects p 
            JOIN users u ON p.customer_id = u.user_id 
            JOIN services s ON p.service_id = s.service_id 
            ORDER BY p.created_at DESC LIMIT 5
        """)
        stats['maintenance_mode'] = is_maintenance_mode()
        stats['maintenance_message'] = get_maintenance_message()
    else:  # ProjectManager
        stats['assigned_projects'] = query_one("SELECT COUNT(*) as count FROM projects WHERE assigned_to = ?", [session['user_id']])['count']
        stats['completed_by_me'] = query_one("SELECT COUNT(*) as count FROM projects WHERE assigned_to = ? AND status = 'Completed'", [session['user_id']])['count']
        stats['pending_my'] = query_one("SELECT COUNT(*) as count FROM projects WHERE assigned_to = ? AND status IN ('Pending', 'Confirmed')", [session['user_id']])['count']
        stats['in_progress'] = query_one("SELECT COUNT(*) as count FROM projects WHERE assigned_to = ? AND status = 'In Progress'", [session['user_id']])['count']
        stats['my_projects'] = query_all("""
            SELECT p.*, u.name as customer_name, s.service_name 
            FROM projects p 
            JOIN users u ON p.customer_id = u.user_id 
            JOIN services s ON p.service_id = s.service_id 
            WHERE p.assigned_to = ? 
            ORDER BY p.created_at DESC LIMIT 10
        """, [session['user_id']])
    
    return render_template('admin/dashboard.html', stats=stats)


@admin_bp.route('/maintenance', methods=['POST'])
@require_role(['SuperAdmin'])
def update_maintenance():
    if not verify_csrf_token(request.form.get('csrf_token')):
        flash('Invalid CSRF token', 'danger')
        return redirect(url_for('admin.dashboard'))

    enabled = request.form.get('maintenance_mode') == 'on'
    message = (request.form.get('maintenance_message') or '').strip()
    if not message:
        message = 'We are making improvements and will be back shortly.'

    set_setting('maintenance_mode', 'true' if enabled else 'false', session['user_id'])
    set_setting('maintenance_message', message, session['user_id'])
    log_activity(
        session['user_id'],
        'Update Maintenance Mode',
        f"Maintenance mode {'enabled' if enabled else 'disabled'}",
        request,
    )
    flash(f"Maintenance mode {'enabled' if enabled else 'disabled'}.", 'success')
    return redirect(url_for('admin.dashboard'))
