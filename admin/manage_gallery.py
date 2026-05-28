from flask import render_template, request, redirect, url_for, flash, session, send_file
from includes.auth import require_role
from includes.db import execute, query_all, query_one
from includes.functions import upload_file, log_activity, verify_csrf_token
from admin import admin_bp
import os

@admin_bp.route('/manage_gallery', methods=['GET', 'POST'])
@require_role(['SuperAdmin', 'ProjectManager'])
def manage_gallery():
    if request.method == 'POST':
        if not verify_csrf_token(request.form.get('csrf_token')):
            flash('Invalid CSRF token', 'danger')
            return redirect(url_for('admin.manage_gallery'))
        
        action = request.form.get('action')
        
        if action == 'upload':
            title = request.form.get('title')
            description = request.form.get('description')
            category = request.form.get('category')
            image = request.files.get('image')
            
            if not image or not image.filename:
                flash('Please select an image to upload', 'danger')
                return redirect(url_for('admin.manage_gallery'))
            
            image_path = upload_file(image, 'gallery')
            
            if image_path:
                gallery_id = execute("""
                    INSERT INTO gallery (title, description, image_path, category, uploaded_by)
                    VALUES (?, ?, ?, ?, ?)
                """, [title, description, image_path, category, session['user_id']])
                
                log_activity(session['user_id'], 'Upload Gallery', f"Uploaded image: {title} (ID: {gallery_id})", request)
                flash('Image uploaded successfully', 'success')
            else:
                flash('Failed to upload image. Check file type and size.', 'danger')
        
        elif action == 'update':
            gallery_id = request.form.get('gallery_id')
            title = request.form.get('title')
            description = request.form.get('description')
            category = request.form.get('category')
            
            execute("""
                UPDATE gallery 
                SET title = ?, description = ?, category = ?
                WHERE gallery_id = ?
            """, [title, description, category, gallery_id])
            
            log_activity(session['user_id'], 'Update Gallery', f"Updated gallery image ID: {gallery_id}", request)
            flash('Image details updated successfully', 'success')
        
        elif action == 'delete':
            gallery_id = request.form.get('gallery_id')
            
            # Get image path to delete file
            image = query_one("SELECT image_path FROM gallery WHERE gallery_id = ?", [gallery_id])
            if image and image['image_path']:
                file_path = image['image_path']
                if os.path.exists(file_path):
                    os.remove(file_path)
            
            execute("DELETE FROM gallery WHERE gallery_id = ?", [gallery_id])
            log_activity(session['user_id'], 'Delete Gallery', f"Deleted gallery image ID: {gallery_id}", request)
            flash('Image deleted successfully', 'success')
    
    images = query_all("""
        SELECT g.*, u.name as uploader_name 
        FROM gallery g
        LEFT JOIN users u ON g.uploaded_by = u.user_id
        ORDER BY g.created_at DESC
    """)
    
    categories = query_all("SELECT DISTINCT category FROM gallery WHERE category IS NOT NULL")
    
    return render_template('admin/manage_gallery.html', images=images, categories=categories)

@admin_bp.route('/gallery_bulk_upload', methods=['POST'])
@require_role(['SuperAdmin', 'ProjectManager'])
def gallery_bulk_upload():
    """Handle multiple image uploads at once"""
    if not verify_csrf_token(request.form.get('csrf_token')):
        return {'error': 'Invalid token'}, 400
    
    files = request.files.getlist('images')
    category = request.form.get('category', 'Uncategorized')
    title_prefix = request.form.get('title_prefix', 'Gallery Image')
    
    uploaded = 0
    failed = 0
    
    for i, file in enumerate(files):
        if file and file.filename:
            image_path = upload_file(file, 'gallery')
            if image_path:
                title = f"{title_prefix} {i+1}"
                execute("""
                    INSERT INTO gallery (title, description, image_path, category, uploaded_by)
                    VALUES (?, ?, ?, ?, ?)
                """, [title, '', image_path, category, session['user_id']])
                uploaded += 1
            else:
                failed += 1
    
    log_activity(session['user_id'], 'Bulk Upload Gallery', f"Uploaded {uploaded} images, {failed} failed", request)
    flash(f'Uploaded {uploaded} images successfully. {failed} failed.', 'success' if uploaded > 0 else 'danger')
    
    return redirect(url_for('admin.manage_gallery'))