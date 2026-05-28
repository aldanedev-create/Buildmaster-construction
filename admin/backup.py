from flask import render_template, request, redirect, url_for, flash, session, send_file, jsonify
from includes.auth import require_role
from includes.db import execute, query_all, query_one
from includes.functions import log_activity, verify_csrf_token
from includes.backup import backup_manager
from admin import admin_bp
import os
from datetime import datetime

@admin_bp.route('/backup')
@require_role(['SuperAdmin'])
def backup():
    backups = backup_manager.get_backup_list()
    
    # Calculate total backup size
    total_size = sum(b.get('backup_size', 0) for b in backups)
    
    # Get backup statistics
    stats = {
        'total_backups': len(backups),
        'total_size_mb': round(total_size / (1024 * 1024), 2),
        'last_backup': backups[0]['created_at'] if backups else 'Never',
        'backup_enabled': True
    }
    
    return render_template('admin/backup.html', backups=backups, stats=stats)

@admin_bp.route('/create_backup', methods=['POST'])
@require_role(['SuperAdmin'])
def create_backup():
    if not verify_csrf_token(request.form.get('csrf_token')):
        flash('Invalid CSRF token', 'danger')
        return redirect(url_for('admin.backup'))
    
    backup_type = request.form.get('backup_type', 'full')
    
    try:
        backup_filename = backup_manager.create_backup(session['user_id'], backup_type)
        log_activity(session['user_id'], 'Create Backup', f"Created backup: {backup_filename}", request)
        flash(f'Backup created successfully: {backup_filename}', 'success')
    except Exception as e:
        flash(f'Backup failed: {str(e)}', 'danger')
    
    return redirect(url_for('admin.backup'))

@admin_bp.route('/download_backup/<filename>')
@require_role(['SuperAdmin'])
def download_backup(filename):
    # Security: prevent path traversal
    if '..' in filename or filename.startswith('/'):
        flash('Invalid filename', 'danger')
        return redirect(url_for('admin.backup'))
    
    backup_path = os.path.join(backup_manager.backup_dir, filename)
    
    if not os.path.exists(backup_path):
        flash('Backup file not found', 'danger')
        return redirect(url_for('admin.backup'))
    
    log_activity(session['user_id'], 'Download Backup', f"Downloaded backup: {filename}", request)
    
    return send_file(
        backup_path,
        as_attachment=True,
        download_name=filename,
        mimetype='application/zip'
    )

@admin_bp.route('/restore_backup/<filename>', methods=['POST'])
@require_role(['SuperAdmin'])
def restore_backup(filename):
    if not verify_csrf_token(request.form.get('csrf_token')):
        flash('Invalid CSRF token', 'danger')
        return redirect(url_for('admin.backup'))
    
    # Confirm restore
    confirm = request.form.get('confirm')
    if confirm != 'YES':
        flash('Please type "YES" to confirm restore', 'danger')
        return redirect(url_for('admin.backup'))
    
    try:
        success, message = backup_manager.restore_backup(filename)
        if success:
            log_activity(session['user_id'], 'Restore Backup', f"Restored from backup: {filename}", request)
            flash(message, 'success')
        else:
            flash(message, 'danger')
    except Exception as e:
        flash(f'Restore failed: {str(e)}', 'danger')
    
    return redirect(url_for('admin.backup'))

@admin_bp.route('/delete_backup/<filename>', methods=['POST'])
@require_role(['SuperAdmin'])
def delete_backup(filename):
    if not verify_csrf_token(request.form.get('csrf_token')):
        flash('Invalid CSRF token', 'danger')
        return redirect(url_for('admin.backup'))
    
    backup_path = os.path.join(backup_manager.backup_dir, filename)
    
    if os.path.exists(backup_path):
        os.remove(backup_path)
        execute("DELETE FROM backup_logs WHERE backup_filename = ?", [filename])
        log_activity(session['user_id'], 'Delete Backup', f"Deleted backup: {filename}", request)
        flash('Backup deleted successfully', 'success')
    else:
        flash('Backup file not found', 'danger')
    
    return redirect(url_for('admin.backup'))

@admin_bp.route('/backup_settings', methods=['POST'])
@require_role(['SuperAdmin'])
def backup_settings():
    if not verify_csrf_token(request.form.get('csrf_token')):
        flash('Invalid CSRF token', 'danger')
        return redirect(url_for('admin.backup'))
    
    auto_backup = request.form.get('auto_backup') == 'on'
    backup_frequency = request.form.get('backup_frequency', 'daily')
    backup_time = request.form.get('backup_time', '02:00')
    retention_days = request.form.get('retention_days', 30)
    
    # Save settings to database or config file
    execute("""
        INSERT OR REPLACE INTO system_settings (setting_key, setting_value)
        VALUES (?, ?)
    """, ['auto_backup', '1' if auto_backup else '0'])
    
    execute("""
        INSERT OR REPLACE INTO system_settings (setting_key, setting_value)
        VALUES (?, ?)
    """, ['backup_frequency', backup_frequency])
    
    execute("""
        INSERT OR REPLACE INTO system_settings (setting_key, setting_value)
        VALUES (?, ?)
    """, ['backup_time', backup_time])
    
    execute("""
        INSERT OR REPLACE INTO system_settings (setting_key, setting_value)
        VALUES (?, ?)
    """, ['backup_retention_days', retention_days])
    
    log_activity(session['user_id'], 'Update Backup Settings', "Updated backup configuration", request)
    flash('Backup settings saved successfully', 'success')
    
    return redirect(url_for('admin.backup'))

# System settings table (add to schema.sql)
def create_settings_table():
    from includes.db import execute
    execute("""
        CREATE TABLE IF NOT EXISTS system_settings (
            setting_key TEXT PRIMARY KEY,
            setting_value TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)