import os
from datetime import timedelta

from flask import Flask, flash, make_response, redirect, render_template, request, send_from_directory, session, url_for

from admin import admin_bp
from config.config import Config
from contact import contact_page, save_contact_message
from includes.auth import (
    generate_reset_token,
    hash_password,
    login_user,
    permanently_delete_old_accounts,
    register_user,
    reset_password,
    soft_delete_account,
    validate_password,
    verify_password,
    verify_reset_token,
)
from includes.db import execute, init_db, query_all, query_one
from includes.functions import (
    generate_csrf_token,
    log_activity,
    send_email,
    send_whatsapp_notification,
    verify_csrf_token,
)
from includes.settings import get_maintenance_message, is_maintenance_mode
from includes.two_factor import create_and_send_2fa_code, disable_2fa, enable_2fa, is_2fa_enabled, verify_2fa_code


app = Flask(__name__)
app.config.from_object(Config)
app.secret_key = Config.SECRET_KEY
app.permanent_session_lifetime = timedelta(days=365)
app.register_blueprint(admin_bp)

init_db()


@app.before_request
def cleanup_old_accounts():
    permanently_delete_old_accounts()


@app.before_request
def enforce_maintenance_mode():
    if not is_maintenance_mode():
        return None

    allowed_endpoints = {
        "maintenance",
        "login",
        "logout",
        "verify_2fa",
        "static",
        "uploaded_file",
    }
    if request.endpoint in allowed_endpoints:
        return None
    if session.get("role") in ["SuperAdmin", "ProjectManager"]:
        return None
    return render_template("maintenance.html", message=get_maintenance_message()), 503


@app.context_processor
def context_processor():
    return {"session": session, "csrf_token": generate_csrf_token()}


@app.route("/maintenance")
def maintenance():
    return render_template("maintenance.html", message=get_maintenance_message()), 503


@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(Config.UPLOAD_FOLDER, filename)


@app.route("/")
def index():
    services = query_all("SELECT * FROM services WHERE is_active = 1 LIMIT 6")
    projects = query_all("SELECT * FROM projects WHERE status = 'Completed' LIMIT 3")
    return render_template("index.html", services=services, projects=projects)


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/services")
def services():
    services = query_all("SELECT * FROM services WHERE is_active = 1")
    return render_template("services.html", services=services)


@app.route("/gallery")
def gallery():
    category = request.args.get("category", "all")
    if category == "all":
        images = query_all("SELECT * FROM gallery ORDER BY created_at DESC")
    else:
        images = query_all("SELECT * FROM gallery WHERE category = ? ORDER BY created_at DESC", [category])
    return render_template("gallery.html", images=images, current_category=category)


@app.route("/request-quote", methods=["GET", "POST"])
def request_quote():
    if request.method == "GET":
        services = query_all("SELECT * FROM services WHERE is_active = 1")
        return render_template("project_request.html", services=services)

    if not verify_csrf_token(request.form.get("csrf_token")):
        flash("Invalid CSRF token", "danger")
        return redirect(url_for("request_quote"))

    pending_project = {
        "service_id": request.form.get("service_id"),
        "description": request.form.get("description"),
        "budget": request.form.get("budget"),
        "location": request.form.get("location"),
    }
    if "user_id" not in session:
        session["pending_project"] = pending_project
        flash("Please login to submit your project request", "info")
        return redirect(url_for("login"))

    project_id = _create_project(session["user_id"], pending_project)
    log_activity(session["user_id"], "Project Request", f"Created project #{project_id}", request)
    flash("Project request submitted successfully.", "success")
    return redirect(url_for("project_confirmation", project_id=project_id))


def _create_project(user_id, payload):
    return execute(
        """
        INSERT INTO projects (customer_id, service_id, project_description, budget, location, status)
        VALUES (?, ?, ?, ?, ?, 'Pending')
        """,
        [user_id, payload.get("service_id"), payload.get("description"), payload.get("budget"), payload.get("location")],
    )


@app.route("/project-confirmation/<int:project_id>")
def project_confirmation(project_id):
    if "user_id" not in session:
        flash("Please login to view your project confirmation", "warning")
        return redirect(url_for("login"))

    project = query_one(
        """
        SELECT p.*, s.service_name
        FROM projects p
        JOIN services s ON p.service_id = s.service_id
        WHERE p.project_id = ?
        """,
        [project_id],
    )
    if not project:
        flash("Project not found", "danger")
        return redirect(url_for("projects"))
    if session.get("role") == "Customer" and project["customer_id"] != session["user_id"]:
        flash("Access denied", "danger")
        return redirect(url_for("projects"))

    return render_template("project_confirmation.html", project=project)


@app.route("/projects")
def projects():
    if "user_id" not in session:
        flash("Please login to view your projects", "warning")
        return redirect(url_for("login"))

    if session.get("role") == "Customer":
        user_projects = query_all(
            """
            SELECT p.*, s.service_name
            FROM projects p
            JOIN services s ON p.service_id = s.service_id
            WHERE p.customer_id = ?
            ORDER BY p.created_at DESC
            """,
            [session["user_id"]],
        )
    elif session.get("role") == "ProjectManager":
        user_projects = query_all(
            """
            SELECT p.*, s.service_name, u.name as customer_name
            FROM projects p
            JOIN services s ON p.service_id = s.service_id
            JOIN users u ON p.customer_id = u.user_id
            WHERE p.assigned_to = ? OR p.assigned_to IS NULL
            ORDER BY p.created_at DESC
            """,
            [session["user_id"]],
        )
    else:
        user_projects = query_all(
            """
            SELECT p.*, s.service_name, u.name as customer_name
            FROM projects p
            JOIN services s ON p.service_id = s.service_id
            JOIN users u ON p.customer_id = u.user_id
            ORDER BY p.created_at DESC
            """
        )
    return render_template("projects.html", projects=user_projects)


@app.route("/project/<int:project_id>")
def project_detail(project_id):
    if "user_id" not in session:
        flash("Please login to view project details", "warning")
        return redirect(url_for("login"))

    project = query_one(
        """
        SELECT p.*, s.service_name, u.name as customer_name, u.email as customer_email, u.phone as customer_phone
        FROM projects p
        JOIN services s ON p.service_id = s.service_id
        JOIN users u ON p.customer_id = u.user_id
        WHERE p.project_id = ?
        """,
        [project_id],
    )
    if not project:
        flash("Project not found", "danger")
        return redirect(url_for("projects"))
    if session["role"] == "Customer" and project["customer_id"] != session["user_id"]:
        flash("Access denied", "danger")
        return redirect(url_for("projects"))

    updates = query_all("SELECT * FROM project_updates WHERE project_id = ? ORDER BY created_at DESC", [project_id])
    return render_template("project_detail.html", project=project, updates=updates)


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")

    email = request.form.get("email")
    password = request.form.get("password")
    success, message, user_data = login_user(email, password, request)
    if not success:
        flash(message, "danger")
        return render_template("login.html")

    if message == "2FA Required":
        session["2fa_user_id"] = user_data["user_id"]
        session["2fa_name"] = user_data["name"]
        try:
            create_and_send_2fa_code(user_data)
            flash("A verification code was sent to your email.", "info")
        except Exception as exc:
            flash(str(exc), "danger")
            return render_template("login.html")
        return redirect(url_for("verify_2fa"))

    _complete_login(user_data)
    response = make_response(redirect(url_for("index")))
    if request.form.get("remember_me"):
        response.set_cookie("user_email", email, max_age=30 * 24 * 60 * 60, httponly=True, samesite="Lax")
    return response


def _complete_login(user_data):
    session.permanent = True
    session["user_id"] = user_data["user_id"]
    session["user_name"] = user_data["name"]
    session["user_email"] = user_data["email"]
    session["role"] = user_data["role"]
    if "pending_project" in session:
        project_id = _create_project(user_data["user_id"], session.pop("pending_project"))
        log_activity(user_data["user_id"], "Project Request", f"Created pending project #{project_id}", request)
        flash("Your project request has been submitted.", "success")


@app.route("/verify-2fa", methods=["GET", "POST"])
def verify_2fa():
    if "2fa_user_id" not in session:
        return redirect(url_for("login"))
    if request.method == "GET":
        return render_template("verify_2fa.html")

    if verify_2fa_code(session["2fa_user_id"], request.form.get("code")):
        user = query_one("SELECT user_id, name, email, role FROM users WHERE user_id = ?", [session["2fa_user_id"]])
        session.pop("2fa_user_id", None)
        session.pop("2fa_name", None)
        _complete_login(user)
        flash("2FA verification successful.", "success")
        return redirect(url_for("index"))

    flash("Invalid or expired 2FA code", "danger")
    return render_template("verify_2fa.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")
    if not verify_csrf_token(request.form.get("csrf_token")):
        flash("Invalid CSRF token", "danger")
        return render_template("register.html")
    if request.form.get("password") != request.form.get("confirm_password"):
        flash("Passwords do not match", "danger")
        return render_template("register.html")

    success, message = register_user(
        request.form.get("name"),
        request.form.get("email"),
        request.form.get("phone"),
        request.form.get("password"),
    )
    flash(message, "success" if success else "danger")
    return redirect(url_for("login")) if success else render_template("register.html")


@app.route("/account", methods=["GET", "POST"])
def account():
    if "user_id" not in session:
        flash("Please login to access your account", "warning")
        return redirect(url_for("login"))

    user = query_one("SELECT * FROM users WHERE user_id = ?", [session["user_id"]])
    if request.method == "GET":
        project_stats = {
            "total": 0,
            "pending": 0,
            "confirmed": 0,
            "in_progress": 0,
            "completed": 0,
            "latest": None,
            "progress_percent": 0,
        }
        if session.get("role") == "Customer":
            rows = query_all(
                """
                SELECT status, project_id, created_at
                FROM projects
                WHERE customer_id = ?
                ORDER BY created_at DESC
                """,
                [session["user_id"]],
            )
            project_stats["total"] = len(rows)
            project_stats["pending"] = sum(1 for row in rows if row["status"] == "Pending")
            project_stats["confirmed"] = sum(1 for row in rows if row["status"] == "Confirmed")
            project_stats["in_progress"] = sum(1 for row in rows if row["status"] == "In Progress")
            project_stats["completed"] = sum(1 for row in rows if row["status"] == "Completed")
            project_stats["latest"] = rows[0] if rows else None
            if rows:
                project_stats["progress_percent"] = round((project_stats["completed"] / len(rows)) * 100)

        return render_template(
            "account.html",
            user=user,
            two_factor_enabled=is_2fa_enabled(session["user_id"]),
            project_stats=project_stats,
        )
    if not verify_csrf_token(request.form.get("csrf_token")):
        flash("Invalid CSRF token", "danger")
        return redirect(url_for("account"))

    action = request.form.get("action")
    if action == "update_profile":
        execute(
            "UPDATE users SET name = ?, phone = ?, address = ?, updated_at = CURRENT_TIMESTAMP WHERE user_id = ?",
            [request.form.get("name"), request.form.get("phone"), request.form.get("address"), session["user_id"]],
        )
        session["user_name"] = request.form.get("name")
        log_activity(session["user_id"], "Profile Updated", "User updated profile information", request)
        flash("Profile updated successfully", "success")
    elif action == "change_password":
        if not verify_password(request.form.get("current_password"), user["password_hash"]):
            flash("Current password is incorrect", "danger")
            return redirect(url_for("account"))
        if request.form.get("new_password") != request.form.get("confirm_password"):
            flash("New passwords do not match", "danger")
            return redirect(url_for("account"))
        valid, msg = validate_password(request.form.get("new_password"))
        if not valid:
            flash(msg, "danger")
            return redirect(url_for("account"))
        execute("UPDATE users SET password_hash = ? WHERE user_id = ?", [hash_password(request.form.get("new_password")), session["user_id"]])
        log_activity(session["user_id"], "Password Changed", "User changed password", request)
        flash("Password changed successfully", "success")
    elif action == "delete_account":
        soft_delete_account(session["user_id"], request)
        session.clear()
        flash("Your account has been scheduled for deletion.", "info")
        return redirect(url_for("index"))
    elif action == "enable_2fa":
        enable_2fa(session["user_id"], request)
        flash("Email 2FA enabled. Login codes will be sent to your Gmail-backed SMTP address.", "success")
    elif action == "disable_2fa":
        disable_2fa(session["user_id"], request)
        flash("Two-factor authentication disabled", "info")
    return redirect(url_for("account"))


@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "GET":
        return render_template("forgot_password.html")
    if not verify_csrf_token(request.form.get("csrf_token")):
        flash("Invalid CSRF token", "danger")
        return redirect(url_for("forgot_password"))

    email = request.form.get("email")
    user = query_one("SELECT user_id FROM users WHERE email = ? AND account_status = 'Active'", [email])
    if user:
        token = generate_reset_token(email)
        reset_link = url_for("reset_password_page", token=token, _external=True)
        sent = send_email(
            email,
            "BuildMaster Password Reset",
            f"""
            <h2>Password Reset Request</h2>
            <p>Click the link below to reset your password. This link expires in 24 hours.</p>
            <p><a href="{reset_link}">Reset Password</a></p>
            <p>If you did not request this, you can ignore this email.</p>
            """,
        )
        if not sent:
            flash("Password reset email could not be sent. Please check the Gmail SMTP settings.", "danger")
            return redirect(url_for("forgot_password"))

    flash("If an account exists with that email, a reset link has been sent", "info")
    return redirect(url_for("login"))


@app.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password_page(token):
    if request.method == "GET":
        if not verify_reset_token(token):
            flash("Invalid or expired reset token", "danger")
            return redirect(url_for("login"))
        return render_template("reset_password.html", token=token)

    if not verify_csrf_token(request.form.get("csrf_token")):
        flash("Invalid CSRF token", "danger")
        return render_template("reset_password.html", token=token)
    if request.form.get("password") != request.form.get("confirm_password"):
        flash("Passwords do not match", "danger")
        return render_template("reset_password.html", token=token)
    success, message = reset_password(token, request.form.get("password"))
    flash(message, "success" if success else "danger")
    return redirect(url_for("login")) if success else render_template("reset_password.html", token=token)


@app.route("/logout")
def logout():
    if "user_id" in session:
        log_activity(session["user_id"], "Logout", "User logged out", request)
    response = make_response(redirect(url_for("index")))
    response.set_cookie("user_email", "", expires=0)
    session.clear()
    flash("You have been logged out", "info")
    return response


@app.route("/contact", methods=["GET", "POST"])
def contact():
    return contact_page() if request.method == "GET" else save_contact_message()


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
