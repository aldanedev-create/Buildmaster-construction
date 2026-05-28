from flask import flash, redirect, render_template, request, url_for

from config.config import Config
from includes.db import execute
from includes.functions import sanitize_input, send_email, validate_email, verify_csrf_token


def contact_page():
    return render_template('contact.html')


def save_contact_message():
    if not verify_csrf_token(request.form.get('csrf_token')):
        flash('Invalid CSRF token', 'danger')
        return redirect(url_for('contact'))

    name = sanitize_input(request.form.get('name'))
    email = sanitize_input(request.form.get('email'))
    subject = sanitize_input(request.form.get('subject') or 'Website inquiry')
    message = sanitize_input(request.form.get('message'))

    if not all([name, email, message]):
        flash('Please complete all required fields.', 'danger')
        return redirect(url_for('contact'))

    if not validate_email(email):
        flash('Please enter a valid email address.', 'danger')
        return redirect(url_for('contact'))

    execute(
        "INSERT INTO messages (name, email, subject, message) VALUES (?, ?, ?, ?)",
        [name, email, subject, message],
    )

    admin_email = Config.ADMIN_ALERT_EMAIL or Config.SMTP_USERNAME
    if admin_email:
        send_email(
            admin_email,
            f"New BuildMaster contact: {subject}",
            f"<p><strong>Name:</strong> {name}</p><p><strong>Email:</strong> {email}</p><p>{message}</p>",
        )

    flash('Message sent successfully. We will contact you soon.', 'success')
    return redirect(url_for('contact'))

