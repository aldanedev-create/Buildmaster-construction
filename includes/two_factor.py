import secrets
from datetime import datetime

from config.config import Config
from includes.db import execute, query_one
from includes.functions import log_activity, send_email


def generate_2fa_code():
    return f"{secrets.randbelow(1000000):06d}"


def store_2fa_code(user_id, code):
    execute("DELETE FROM two_fa_codes WHERE user_id = ?", [user_id])
    execute("INSERT INTO two_fa_codes (user_id, code) VALUES (?, ?)", [user_id, code])


def send_2fa_email(user_email, code, user_name):
    body = f"""
    <h2>Your BuildMaster verification code</h2>
    <p>Hi {user_name},</p>
    <p>Your verification code is <strong>{code}</strong>.</p>
    <p>This code expires in 10 minutes. If you did not try to sign in, change your password immediately.</p>
    """
    if not send_email(user_email, "BuildMaster verification code", body):
        raise RuntimeError("Could not send 2FA email. Check Gmail SMTP settings.")


def create_and_send_2fa_code(user):
    code = generate_2fa_code()
    store_2fa_code(user["user_id"], code)
    send_2fa_email(user["email"], code, user["name"])


def verify_2fa_code(user_id, submitted_code):
    submitted_code = (submitted_code or "").strip().replace(" ", "")
    record = query_one(
        """
        SELECT * FROM two_fa_codes
        WHERE user_id = ? AND code = ? AND used = 0
        ORDER BY created_at DESC
        LIMIT 1
        """,
        [user_id, submitted_code],
    )
    if not record:
        return False

    created_at = record["created_at"]
    created = None
    for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S"):
        try:
            created = datetime.strptime(created_at, fmt)
            break
        except (TypeError, ValueError):
            continue

    if not created or (datetime.now() - created).total_seconds() > 600:
        return False

    execute("UPDATE two_fa_codes SET used = 1 WHERE id = ?", [record["id"]])
    return True


def enable_2fa(user_id, request=None):
    execute("UPDATE users SET two_factor_enabled = 1, two_factor_secret = NULL WHERE user_id = ?", [user_id])
    log_activity(user_id, "Enable 2FA", "Email two-factor authentication enabled", request)


def disable_2fa(user_id, request=None):
    execute("UPDATE users SET two_factor_enabled = 0, two_factor_secret = NULL WHERE user_id = ?", [user_id])
    execute("DELETE FROM two_fa_codes WHERE user_id = ?", [user_id])
    log_activity(user_id, "Disable 2FA", "Email two-factor authentication disabled", request)


def is_2fa_enabled(user_id):
    user = query_one("SELECT two_factor_enabled FROM users WHERE user_id = ?", [user_id])
    return bool(user and user["two_factor_enabled"])





