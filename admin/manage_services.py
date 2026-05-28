from flask import render_template, request, redirect, url_for, flash, session
from includes.auth import require_role
from includes.db import execute, query_all, query_one
from includes.functions import upload_file, log_activity, verify_csrf_token
from admin import admin_bp


@admin_bp.route('/manage_services', methods=['GET', 'POST'])
@require_role(['SuperAdmin'])
def manage_services():
    if request.method == 'POST':
        if not verify_csrf_token(request.form.get('csrf_token')):
            flash('Invalid CSRF token', 'danger')
            return redirect(url_for('admin.manage_services'))

        action = request.form.get('action')

        if action == 'add':
            name        = request.form.get('service_name', '').strip()
            description = request.form.get('description', '').strip()
            category    = request.form.get('category', '').strip()
            image       = request.files.get('image')
            image_path  = upload_file(image, 'services') if image and image.filename else None

            sid = execute(
                "INSERT INTO services (service_name, description, image_path, category, created_by) VALUES (?, ?, ?, ?, ?)",
                [name, description, image_path, category, session['user_id']]
            )
            log_activity(session['user_id'], 'Add Service', f"Added: {name} (ID:{sid})", request)
            flash('Service added successfully', 'success')

        elif action == 'edit':
            sid         = request.form.get('service_id')
            name        = request.form.get('service_name', '').strip()
            description = request.form.get('description', '').strip()
            category    = request.form.get('category', '').strip()
            image       = request.files.get('image')

            if image and image.filename:
                # New image uploaded — replace old one
                image_path = upload_file(image, 'services')
                execute(
                    """UPDATE services SET service_name=?, description=?, category=?,
                       image_path=?, updated_at=CURRENT_TIMESTAMP WHERE service_id=?""",
                    [name, description, category, image_path, sid]
                )
            else:
                # Keep existing image
                execute(
                    """UPDATE services SET service_name=?, description=?, category=?,
                       updated_at=CURRENT_TIMESTAMP WHERE service_id=?""",
                    [name, description, category, sid]
                )
            log_activity(session['user_id'], 'Edit Service', f"Edited ID:{sid}", request)
            flash('Service updated successfully', 'success')

        elif action == 'delete':
            sid = request.form.get('service_id')
            execute("UPDATE services SET is_active=0 WHERE service_id=?", [sid])
            log_activity(session['user_id'], 'Deactivate Service', f"Deactivated ID:{sid}", request)
            flash('Service deactivated', 'success')

        elif action == 'restore':
            sid = request.form.get('service_id')
            execute("UPDATE services SET is_active=1 WHERE service_id=?", [sid])
            log_activity(session['user_id'], 'Restore Service', f"Restored ID:{sid}", request)
            flash('Service restored', 'success')

    services = query_all("SELECT * FROM services ORDER BY is_active DESC, created_at DESC")
    return render_template('admin/manage_services.html', services=services)