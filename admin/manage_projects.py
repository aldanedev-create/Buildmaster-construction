from flask import render_template, request, redirect, url_for, flash, session, jsonify
from includes.auth import require_role
from includes.db import execute, query_all, query_one
from includes.functions import log_activity, verify_csrf_token, upload_file, send_whatsapp_notification
from admin import admin_bp

@admin_bp.route('/manage_projects')
@require_role(['SuperAdmin', 'ProjectManager'])
def manage_projects():
    if session['role'] == 'SuperAdmin':
        projects = query_all("""
            SELECT p.*, u.name as customer_name, u.email as customer_email, u.phone as customer_phone,
                   s.service_name, pm.name as manager_name
            FROM projects p 
            JOIN users u ON p.customer_id = u.user_id
            JOIN services s ON p.service_id = s.service_id
            LEFT JOIN users pm ON p.assigned_to = pm.user_id
            ORDER BY p.created_at DESC
        """)
        managers = query_all("SELECT user_id, name, email FROM users WHERE role = 'ProjectManager' AND account_status = 'Active'")
    else:
        projects = query_all("""
            SELECT p.*, u.name as customer_name, u.email as customer_email, u.phone as customer_phone,
                   s.service_name
            FROM projects p 
            JOIN users u ON p.customer_id = u.user_id
            JOIN services s ON p.service_id = s.service_id
            WHERE p.assigned_to = ? OR (p.assigned_to IS NULL AND p.status != 'Completed')
            ORDER BY p.created_at DESC
        """, [session['user_id']])
        managers = []
    
    return render_template('admin/manage_projects.html', projects=projects, managers=managers)

@admin_bp.route('/update_project/<int:project_id>', methods=['POST'])
@require_role(['SuperAdmin', 'ProjectManager'])
def update_project(project_id):
    if not verify_csrf_token(request.form.get('csrf_token')):
        flash('Invalid CSRF token', 'danger')
        return redirect(url_for('admin.manage_projects'))
    
    status = request.form.get('status')
    assigned_to = request.form.get('assigned_to')
    update_description = request.form.get('update_description')
    
    # Update status
    if status:
        old_status = query_one("SELECT status FROM projects WHERE project_id = ?", [project_id])
        if old_status:
            execute("UPDATE projects SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE project_id = ?", [status, project_id])
            log_activity(session['user_id'], 'Update Project Status', f"Project #{project_id} status changed from {old_status['status']} to {status}", request)
            
            # Send WhatsApp notification to customer
            project = query_one("SELECT customer_id FROM projects WHERE project_id = ?", [project_id])
            if project:
                customer = query_one("SELECT phone, name FROM users WHERE user_id = ?", [project['customer_id']])
                if customer and customer['phone']:
                    message = f"Dear {customer['name']}, your project #{project_id} status has been updated to: {status}. Track your project at: https://buildmaster.com/projects"
                    send_whatsapp_notification(customer['phone'], message)
    
    # Assign project manager (SuperAdmin only)
    if assigned_to and session['role'] == 'SuperAdmin':
        execute("UPDATE projects SET assigned_to = ? WHERE project_id = ?", [assigned_to, project_id])
        log_activity(session['user_id'], 'Assign Project', f"Assigned project #{project_id} to manager ID: {assigned_to}", request)
        
        # Notify the assigned manager
        manager = query_one("SELECT phone, name FROM users WHERE user_id = ?", [assigned_to])
        if manager and manager['phone']:
            message = f"You have been assigned to project #{project_id}. Please review and update status."
            send_whatsapp_notification(manager['phone'], message)
    
    # Add project update
    if update_description:
        image = request.files.get('update_image')
        image_path = upload_file(image, 'project_images') if image and image.filename else None
        
        execute("""
            INSERT INTO project_updates (project_id, update_description, image_path, created_by)
            VALUES (?, ?, ?, ?)
        """, [project_id, update_description, image_path, session['user_id']])
        log_activity(session['user_id'], 'Add Project Update', f"Added update to project #{project_id}", request)
        
        # Send update notification to customer
        project = query_one("SELECT customer_id FROM projects WHERE project_id = ?", [project_id])
        if project:
            customer = query_one("SELECT phone, name FROM users WHERE user_id = ?", [project['customer_id']])
            if customer and customer['phone']:
                message = f"Dear {customer['name']}, new update on your project #{project_id}: {update_description[:100]}"
                send_whatsapp_notification(customer['phone'], message)
    
    flash('Project updated successfully', 'success')
    return redirect(request.referrer or url_for('admin.manage_projects'))

@admin_bp.route('/get_project/<int:project_id>')
@require_role(['SuperAdmin', 'ProjectManager'])
def get_project(project_id):
    """AJAX endpoint to get project details"""
    project = query_one("""
        SELECT p.*, u.name as customer_name, u.email as customer_email, u.phone as customer_phone,
               s.service_name
        FROM projects p 
        JOIN users u ON p.customer_id = u.user_id
        JOIN services s ON p.service_id = s.service_id
        WHERE p.project_id = ?
    """, [project_id])
    
    updates = query_all("SELECT * FROM project_updates WHERE project_id = ? ORDER BY created_at DESC", [project_id])
    
    return jsonify({
        'project': project,
        'updates': updates
    })

@admin_bp.route('/delete_project/<int:project_id>', methods=['POST'])
@require_role(['SuperAdmin'])
def delete_project(project_id):
    if not verify_csrf_token(request.form.get('csrf_token')):
        return jsonify({'error': 'Invalid token'}), 400
    
    execute("DELETE FROM projects WHERE project_id = ?", [project_id])
    log_activity(session['user_id'], 'Delete Project', f"Permanently deleted project #{project_id}", request)
    
    flash('Project deleted successfully', 'success')
    return redirect(url_for('admin.manage_projects'))