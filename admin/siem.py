from flask import flash, redirect, render_template, request, session, url_for

from admin import admin_bp
from includes.auth import require_role
from includes.db import execute, query_all, query_one
from includes.functions import log_activity, verify_csrf_token


def run_detection_rules():
    failed_login_rows = query_all(
        """
        SELECT ip_address, COUNT(*) as attempts, MAX(timestamp) as last_seen
        FROM activity_logs
        WHERE action = 'Failed Login' AND timestamp >= datetime('now', '-1 day')
        GROUP BY ip_address
        HAVING attempts >= 5
        """
    )
    for row in failed_login_rows:
        existing = query_one(
            """
            SELECT alert_id FROM security_alerts
            WHERE rule_name = 'Repeated failed login' AND source_ip = ? AND status = 'Open'
            """,
            [row['ip_address']],
        )
        if not existing:
            execute(
                """
                INSERT INTO security_alerts (severity, rule_name, description, source_ip)
                VALUES ('High', 'Repeated failed login', ?, ?)
                """,
                [f"{row['attempts']} failed login attempts in the last 24 hours", row['ip_address']],
            )

    sensitive_rows = query_all(
        """
        SELECT log_id, user_id, user_email, action, details, ip_address
        FROM activity_logs
        WHERE action IN ('Delete Customer', 'Delete Admin', 'Create Backup', 'Download Backup')
          AND timestamp >= datetime('now', '-1 day')
        ORDER BY timestamp DESC
        LIMIT 50
        """
    )
    for row in sensitive_rows:
        existing = query_one(
            "SELECT alert_id FROM security_alerts WHERE rule_name = ? AND description = ? AND status = 'Open'",
            ['Sensitive admin action', row['details']],
        )
        if not existing:
            execute(
                """
                INSERT INTO security_alerts (severity, rule_name, description, source_ip, user_id)
                VALUES ('Medium', 'Sensitive admin action', ?, ?, ?)
                """,
                [f"{row['user_email'] or 'System'}: {row['action']} - {row['details']}", row['ip_address'], row['user_id']],
            )


@admin_bp.route('/siem')
@require_role(['SuperAdmin'])
def siem():
    run_detection_rules()
    stats = {
        'open_alerts': query_one("SELECT COUNT(*) as count FROM security_alerts WHERE status = 'Open'")['count'],
        'high_alerts': query_one("SELECT COUNT(*) as count FROM security_alerts WHERE status = 'Open' AND severity = 'High'")['count'],
        'events_today': query_one("SELECT COUNT(*) as count FROM activity_logs WHERE timestamp >= date('now')")['count'],
        'unique_ips': query_one("SELECT COUNT(DISTINCT ip_address) as count FROM activity_logs WHERE timestamp >= datetime('now', '-1 day')")['count'],
    }
    alerts = query_all("SELECT * FROM security_alerts ORDER BY created_at DESC LIMIT 100")
    events = query_all("SELECT * FROM activity_logs ORDER BY timestamp DESC LIMIT 100")
    return render_template('admin/siem.html', stats=stats, alerts=alerts, events=events)


@admin_bp.route('/siem/alerts/<int:alert_id>/resolve', methods=['POST'])
@require_role(['SuperAdmin'])
def resolve_alert(alert_id):
    if not verify_csrf_token(request.form.get('csrf_token')):
        flash('Invalid CSRF token', 'danger')
        return redirect(url_for('admin.siem'))

    execute(
        "UPDATE security_alerts SET status = 'Resolved', resolved_at = CURRENT_TIMESTAMP, resolved_by = ? WHERE alert_id = ?",
        [session['user_id'], alert_id],
    )
    log_activity(session['user_id'], 'Resolve SIEM Alert', f"Resolved alert #{alert_id}", request)
    flash('Alert resolved.', 'success')
    return redirect(url_for('admin.siem'))

