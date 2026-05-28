from flask import render_template, request, redirect, url_for, flash, session
from includes.auth import require_role, hash_password, validate_password
from includes.db import execute, query_all, query_one
from includes.functions import log_activity, verify_csrf_token
from admin import admin_bp

@admin_bp.route('/manage_admins')
@require_role(['SuperAdmin'])
def manage_admins():
    admins = query_all("""
        SELECT user_id, name, email, phone, role, account_status, created_at, last_login
        FROM users 
        WHERE role IN ('SuperAdmin', 'ProjectManager')
        ORDER BY 
            CASE WHEN role = 'SuperAdmin' THEN 1 ELSE 2 END,
            created_at
    """)
    return render_template('admin/manage_admins.html', admins=admins)

@admin_bp.route('/create_admin', methods=['POST'])
@require_role(['SuperAdmin'])
def create_admin():
    if not verify_csrf_token(request.form.get('csrf_token')):
        flash('Invalid CSRF token', 'danger')
        return redirect(url_for('admin.manage_admins'))
    
    name = request.form.get('name')
    email = request.form.get('email')
    phone = request.form.get('phone')
    role = request.form.get('role')
    password = request.form.get('password')
    
    if not all([name, email, phone, role, password]):
        flash('All fields are required', 'danger')
        return redirect(url_for('admin.manage_admins'))
    
    # Validate email uniqueness
    existing = query_one("SELECT user_id FROM users WHERE email = ?", [email])
    if existing:
        flash('Email already exists', 'danger')
        return redirect(url_for('admin.manage_admins'))
    
    # Validate password strength for new admin
    valid, msg = validate_password(password)
    if not valid:
        flash(msg, 'danger')
        return redirect(url_for('admin.manage_admins'))
    
    password_hash = hash_password(password)
    
    try:
        user_id = execute("""
            INSERT INTO users (name, email, phone, password_hash, role, account_status)
            VALUES (?, ?, ?, ?, ?, 'Active')
        """, [name, email, phone, password_hash, role])
        
        log_activity(session['user_id'], 'Create Admin', f"Created new {role}: {email} (ID: {user_id})", request)
        flash(f'{role} created successfully. Temporary password: {password}', 'success')
    except Exception as e:
        flash(f'Error creating admin: {str(e)}', 'danger')
    
    return redirect(url_for('admin.manage_admins'))

@admin_bp.route('/edit_admin/<int:user_id>', methods=['POST'])
@require_role(['SuperAdmin'])
def edit_admin(user_id):
    if not verify_csrf_token(request.form.get('csrf_token')):
        flash('Invalid CSRF token', 'danger')
        return redirect(url_for('admin.manage_admins'))
    
    # Prevent editing own role from SuperAdmin
    if user_id == session['user_id']:
        flash('You cannot edit your own role here. Use Account Settings.', 'danger')
        return redirect(url_for('admin.manage_admins'))
    
    name = request.form.get('name')
    phone = request.form.get('phone')
    role = request.form.get('role')
    
    execute("""
        UPDATE users 
        SET name = ?, phone = ?, role = ?, updated_at = CURRENT_TIMESTAMP
        WHERE user_id = ?
    """, [name, phone, role, user_id])
    
    log_activity(session['user_id'], 'Edit Admin', f"Edited admin user ID: {user_id}", request)
    flash('Admin updated successfully', 'success')
    
    return redirect(url_for('admin.manage_admins'))

@admin_bp.route('/reset_admin_password/<int:user_id>', methods=['POST'])
@require_role(['SuperAdmin'])
def reset_admin_password(user_id):
    if not verify_csrf_token(request.form.get('csrf_token')):
        flash('Invalid CSRF token', 'danger')
        return redirect(url_for('admin.manage_admins'))
    
    new_password = request.form.get('new_password')
    
    if not new_password:
        flash('Password is required', 'danger')
        return redirect(url_for('admin.manage_admins'))
    
    valid, msg = validate_password(new_password)
    if not valid:
        flash(msg, 'danger')
        return redirect(url_for('admin.manage_admins'))
    
    password_hash = hash_password(new_password)
    execute("UPDATE users SET password_hash = ? WHERE user_id = ?", [password_hash, user_id])
    
    log_activity(session['user_id'], 'Reset Admin Password', f"Reset password for admin user ID: {user_id}", request)
    flash(f'Password reset successfully. New temporary password: {new_password}', 'success')
    
    return redirect(url_for('admin.manage_admins'))

@admin_bp.route('/delete_admin/<int:user_id>', methods=['POST'])
@require_role(['SuperAdmin'])
def delete_admin(user_id):
    if not verify_csrf_token(request.form.get('csrf_token')):
        flash('Invalid CSRF token', 'danger')
        return redirect(url_for('admin.manage_admins'))
    
    # Prevent deleting own account
    if user_id == session['user_id']:
        flash('You cannot delete your own account', 'danger')
        return redirect(url_for('admin.manage_admins'))
    
    # Check if this is the last SuperAdmin
    admin = query_one("SELECT role FROM users WHERE user_id = ?", [user_id])
    if admin and admin['role'] == 'SuperAdmin':
        superadmin_count = query_one("SELECT COUNT(*) as count FROM users WHERE role = 'SuperAdmin' AND account_status != 'Deleted'")['count']
        if superadmin_count <= 1:
            flash('Cannot delete the last Super Admin account', 'danger')
            return redirect(url_for('admin.manage_admins'))
    
    execute("UPDATE users SET account_status = 'Deleted', deleted_at = CURRENT_TIMESTAMP WHERE user_id = ?", [user_id])
    log_activity(session['user_id'], 'Delete Admin', f"Deleted admin user ID: {user_id}", request)
    flash('Admin account deleted', 'success')
    
    return redirect(url_for('admin.manage_admins'))