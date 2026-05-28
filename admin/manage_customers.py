from flask import render_template, request, redirect, url_for, flash, session, jsonify
from includes.auth import require_role
from includes.db import execute, query_all, query_one
from includes.functions import log_activity, verify_csrf_token
from admin import admin_bp

@admin_bp.route('/manage_customers')
@require_role(['SuperAdmin'])
def manage_customers():
    customers = query_all("""
        SELECT user_id, name, email, phone, role, account_status, created_at, last_login,
               (SELECT COUNT(*) FROM projects WHERE customer_id = users.user_id) as project_count
        FROM users 
        WHERE role = 'Customer'
        ORDER BY created_at DESC
    """)
    return render_template('admin/manage_customers.html', customers=customers)

@admin_bp.route('/toggle_user/<int:user_id>', methods=['POST'])
@require_role(['SuperAdmin'])
def toggle_user(user_id):
    if not verify_csrf_token(request.form.get('csrf_token')):
        flash('Invalid CSRF token', 'danger')
        return redirect(url_for('admin.manage_customers'))
    
    user = query_one("SELECT account_status, email, name FROM users WHERE user_id = ?", [user_id])
    if user:
        new_status = 'Suspended' if user['account_status'] == 'Active' else 'Active'
        execute("UPDATE users SET account_status = ? WHERE user_id = ?", [new_status, user_id])
        log_activity(session['user_id'], 'Toggle User Status', f"User {user['email']} status changed to {new_status}", request)
        flash(f'User {user["name"]} status updated to {new_status}', 'success')
    
    return redirect(url_for('admin.manage_customers'))

@admin_bp.route('/delete_customer/<int:user_id>', methods=['POST'])
@require_role(['SuperAdmin'])
def delete_customer(user_id):
    if not verify_csrf_token(request.form.get('csrf_token')):
        flash('Invalid CSRF token', 'danger')
        return redirect(url_for('admin.manage_customers'))

    user = query_one("SELECT user_id, name, email, role FROM users WHERE user_id = ?", [user_id])
    if not user or user['role'] != 'Customer':
        flash('Customer not found', 'danger')
        return redirect(url_for('admin.manage_customers'))

    execute("UPDATE users SET account_status = 'Deleted', deleted_at = CURRENT_TIMESTAMP WHERE user_id = ?", [user_id])
    log_activity(session['user_id'], 'Delete Customer', f"Deleted customer account {user['email']}", request)
    flash(f'Customer {user["name"]} has been deleted.', 'success')
    return redirect(url_for('admin.manage_customers'))

@admin_bp.route('/view_customer/<int:user_id>')
@require_role(['SuperAdmin'])
def view_customer(user_id):
    customer = query_one("""
        SELECT * FROM users WHERE user_id = ? AND role = 'Customer'
    """, [user_id])
    
    if not customer:
        flash('Customer not found', 'danger')
        return redirect(url_for('admin.manage_customers'))
    
    projects = query_all("""
        SELECT p.*, s.service_name 
        FROM projects p 
        JOIN services s ON p.service_id = s.service_id 
        WHERE p.customer_id = ? 
        ORDER BY p.created_at DESC
    """, [user_id])
    
    payments = query_all("""
        SELECT p.*, pr.project_id, pr.location 
        FROM payments p 
        JOIN projects pr ON p.project_id = pr.project_id 
        WHERE pr.customer_id = ?
    """, [user_id])
    
    return render_template('admin/view_customer.html', customer=customer, projects=projects, payments=payments)
