import csv
from datetime import datetime, timedelta
from io import BytesIO, StringIO

from flask import jsonify, render_template, request, send_file, session

from admin import admin_bp
from includes.auth import require_role
from includes.db import query_all, query_one
from includes.functions import log_activity


@admin_bp.route('/reports')
@require_role(['SuperAdmin'])
def reports():
    stats = {
        'projects': query_one("SELECT COUNT(*) as count FROM projects")['count'],
        'pending': query_one("SELECT COUNT(*) as count FROM projects WHERE status = 'Pending'")['count'],
        'customers': query_one("SELECT COUNT(*) as count FROM users WHERE role = 'Customer' AND account_status != 'Deleted'")['count'],
        'messages': query_one("SELECT COUNT(*) as count FROM messages WHERE is_read = 0")['count'],
    }
    return render_template('admin/reports.html', stats=stats)


@admin_bp.route('/reports/project_report')
@require_role(['SuperAdmin'])
def project_report():
    date_from = request.args.get('date_from', (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'))
    date_to = request.args.get('date_to', datetime.now().strftime('%Y-%m-%d'))
    status = request.args.get('status', '')

    query = """
        SELECT p.*, u.name as customer_name, u.email as customer_email, u.phone as customer_phone,
               s.service_name, pm.name as manager_name, COUNT(pu.update_id) as update_count
        FROM projects p
        JOIN users u ON p.customer_id = u.user_id
        JOIN services s ON p.service_id = s.service_id
        LEFT JOIN users pm ON p.assigned_to = pm.user_id
        LEFT JOIN project_updates pu ON p.project_id = pu.project_id
        WHERE DATE(p.created_at) BETWEEN ? AND ?
    """
    params = [date_from, date_to]
    if status:
        query += " AND p.status = ?"
        params.append(status)
    query += " GROUP BY p.project_id ORDER BY p.created_at DESC"

    projects = query_all(query, params)
    stats = {
        'total_projects': len(projects),
        'completed': sum(1 for p in projects if p['status'] == 'Completed'),
        'pending': sum(1 for p in projects if p['status'] == 'Pending'),
        'in_progress': sum(1 for p in projects if p['status'] == 'In Progress'),
        'unassigned': sum(1 for p in projects if not p.get('assigned_to')),
        'total_budget': sum(p.get('budget', 0) or 0 for p in projects),
    }
    return render_template(
        'admin/project_report.html',
        projects=projects,
        stats=stats,
        date_from=date_from,
        date_to=date_to,
        status=status,
    )


@admin_bp.route('/reports/customer_report')
@require_role(['SuperAdmin'])
def customer_report():
    customers = query_all(
        """
        SELECT u.user_id, u.name, u.email, u.phone, u.account_status, u.created_at, u.last_login,
               COUNT(p.project_id) as project_count,
               MAX(p.created_at) as latest_project
        FROM users u
        LEFT JOIN projects p ON p.customer_id = u.user_id
        WHERE u.role = 'Customer' AND u.account_status != 'Deleted'
        GROUP BY u.user_id
        ORDER BY u.created_at DESC
        """
    )
    return render_template('admin/customer_report.html', customers=customers)


@admin_bp.route('/reports/export_csv/<report_type>')
@require_role(['SuperAdmin'])
def export_csv(report_type):
    date_from = request.args.get('date_from', (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'))
    date_to = request.args.get('date_to', datetime.now().strftime('%Y-%m-%d'))
    output = StringIO()
    writer = csv.writer(output)

    if report_type == 'projects':
        rows = query_all(
            """
            SELECT p.project_id, u.name as customer_name, u.email as customer_email, u.phone as customer_phone,
                   s.service_name, p.location, p.budget, p.status, p.created_at, pm.name as manager_name
            FROM projects p
            JOIN users u ON p.customer_id = u.user_id
            JOIN services s ON p.service_id = s.service_id
            LEFT JOIN users pm ON p.assigned_to = pm.user_id
            WHERE DATE(p.created_at) BETWEEN ? AND ?
            ORDER BY p.created_at DESC
            """,
            [date_from, date_to],
        )
        writer.writerow(['Project ID', 'Customer', 'Email', 'Phone', 'Service', 'Location', 'Budget', 'Status', 'Created', 'Manager'])
        for row in rows:
            writer.writerow([
                row['project_id'], row['customer_name'], row['customer_email'], row['customer_phone'],
                row['service_name'], row['location'], row['budget'], row['status'], row['created_at'],
                row['manager_name'] or 'Unassigned',
            ])
        filename = f"projects_report_{date_from}_to_{date_to}.csv"
    elif report_type == 'customers':
        rows = query_all(
            """
            SELECT u.name, u.email, u.phone, u.account_status, u.created_at, u.last_login,
                   COUNT(p.project_id) as project_count
            FROM users u
            LEFT JOIN projects p ON p.customer_id = u.user_id
            WHERE u.role = 'Customer' AND u.account_status != 'Deleted'
            GROUP BY u.user_id
            ORDER BY u.created_at DESC
            """
        )
        writer.writerow(['Customer', 'Email', 'Phone', 'Status', 'Joined', 'Last Login', 'Projects'])
        for row in rows:
            writer.writerow([row['name'], row['email'], row['phone'], row['account_status'], row['created_at'], row['last_login'], row['project_count']])
        filename = "customers_report.csv"
    else:
        return jsonify({'error': 'Invalid report type'}), 400

    data = output.getvalue().encode('utf-8')
    log_activity(session['user_id'], 'Export Report', f"Exported {report_type} report", request)
    return send_file(BytesIO(data), mimetype='text/csv', as_attachment=True, download_name=filename)

