from flask import flash, jsonify, redirect, render_template, request, session, url_for
from includes.auth import require_role
from includes.db import query_all, query_one
from datetime import datetime, timedelta
from admin import admin_bp

@admin_bp.route('/activity_logs')
@require_role(['SuperAdmin', 'ProjectManager'])
def activity_logs():
    page = request.args.get('page', 1, type=int)
    per_page = 50
    offset = (page - 1) * per_page
    
    action_filter = request.args.get('action', '')
    user_filter = request.args.get('user', '')
    date_filter = request.args.get('date', '')
    
    if session['role'] == 'SuperAdmin':
        query = """
            SELECT * FROM activity_logs 
            WHERE 1=1
        """
        params = []
        
        if action_filter:
            query += " AND action LIKE ?"
            params.append(f"%{action_filter}%")
        
        if user_filter:
            query += " AND user_email LIKE ?"
            params.append(f"%{user_filter}%")
        
        if date_filter:
            query += " AND DATE(timestamp) = ?"
            params.append(date_filter)
        
        query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
        params.extend([per_page, offset])
        
        logs = query_all(query, params)
        
        # Get total count for pagination
        count_query = """
            SELECT COUNT(*) as total FROM activity_logs 
            WHERE 1=1
        """
        count_params = []
        if action_filter:
            count_query += " AND action LIKE ?"
            count_params.append(f"%{action_filter}%")
        if user_filter:
            count_query += " AND user_email LIKE ?"
            count_params.append(f"%{user_filter}%")
        if date_filter:
            count_query += " AND DATE(timestamp) = ?"
            count_params.append(date_filter)
        
        total = query_one(count_query, count_params)['total']
        
        # Get unique actions and users for filters
        actions = query_all("SELECT DISTINCT action FROM activity_logs ORDER BY action")
        users = query_all("SELECT DISTINCT user_email FROM activity_logs WHERE user_email IS NOT NULL ORDER BY user_email")
    else:
        # ProjectManager sees only their own activity
        logs = query_all("""
            SELECT * FROM activity_logs 
            WHERE user_id = ? 
            ORDER BY timestamp DESC 
            LIMIT ? OFFSET ?
        """, [session['user_id'], per_page, offset])
        
        total = query_one("SELECT COUNT(*) as total FROM activity_logs WHERE user_id = ?", [session['user_id']])['total']
        actions = []
        users = []
    
    total_pages = (total + per_page - 1) // per_page
    
    return render_template('admin/activity_logs.html', 
                         logs=logs, 
                         page=page, 
                         total_pages=total_pages,
                         total=total,
                         action_filter=action_filter,
                         user_filter=user_filter,
                         date_filter=date_filter,
                         actions=actions,
                         users=users)

@admin_bp.route('/activity_logs/export')
@require_role(['SuperAdmin'])
def export_activity_logs():
    """Export activity logs as CSV"""
    import csv
    from io import StringIO
    from flask import Response
    
    logs = query_all("""
        SELECT * FROM activity_logs 
        ORDER BY timestamp DESC 
        LIMIT 10000
    """)
    
    output = StringIO()
    writer = csv.writer(output)
    
    # Write headers
    writer.writerow(['Log ID', 'User ID', 'User Email', 'Action', 'Details', 'IP Address', 'User Agent', 'Timestamp'])
    
    # Write data
    for log in logs:
        writer.writerow([
            log['log_id'],
            log['user_id'],
            log['user_email'],
            log['action'],
            log['details'],
            log['ip_address'],
            log['user_agent'],
            log['timestamp']
        ])
    
    output.seek(0)
    
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=activity_logs.csv'}
    )

@admin_bp.route('/activity_logs/clear', methods=['POST'])
@require_role(['SuperAdmin'])
def clear_activity_logs():
    from includes.functions import verify_csrf_token, log_activity
    
    if not verify_csrf_token(request.form.get('csrf_token')):
        return jsonify({'error': 'Invalid token'}), 400
    
    days = request.form.get('days', 30, type=int)
    
    # Delete logs older than specified days
    execute("DELETE FROM activity_logs WHERE timestamp <= datetime('now', '-' || ? || ' days')", [days])
    
    log_activity(session['user_id'], 'Clear Activity Logs', f"Cleared logs older than {days} days", request)
    
    flash(f'Activity logs older than {days} days have been cleared', 'success')
    return redirect(url_for('admin.activity_logs'))

def execute(sql, params=None):
    from includes.db import execute as db_execute
    return db_execute(sql, params)
