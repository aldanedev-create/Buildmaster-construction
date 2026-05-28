#!/usr/bin/env python3
"""
reset_admin.py – Run once to set/reset the SuperAdmin password.
Usage:  python reset_admin.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from werkzeug.security import generate_password_hash
import sqlite3

DB_PATH = 'sql/construction.db'
ADMIN_EMAIL = 'admin@construction.com'
NEW_PASSWORD = 'Admin@123!'   # Change this to whatever you want

def reset():
    if not os.path.exists(DB_PATH):
        print(f"[ERROR] Database not found at {DB_PATH}")
        print("Run:  python init_db.py  first.")
        sys.exit(1)

    pw_hash = generate_password_hash(NEW_PASSWORD, method='pbkdf2:sha256')

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")

    # Upsert the super admin row
    conn.execute("""
        INSERT INTO users
            (name, email, phone, password_hash, role, account_status,
             two_fa_enabled, two_fa_method)
        VALUES
            ('Super Admin', ?, '+18761234567', ?, 'SuperAdmin', 'Active', 0, NULL)
        ON CONFLICT(email) DO UPDATE SET
            password_hash    = excluded.password_hash,
            account_status   = 'Active',
            two_fa_enabled   = 0,
            two_fa_method    = NULL,
            deleted_at       = NULL,
            updated_at       = CURRENT_TIMESTAMP
    """, [ADMIN_EMAIL, pw_hash])

    conn.commit()

    # Verify
    cur = conn.execute(
        "SELECT user_id, email, role, account_status, two_fa_enabled FROM users WHERE email=?",
        [ADMIN_EMAIL]
    )
    row = cur.fetchone()
    conn.close()

    if row:
        print("=" * 50)
        print("  SuperAdmin account updated successfully")
        print("=" * 50)
        print(f"  Email    : {row[1]}")
        print(f"  Password : {NEW_PASSWORD}")
        print(f"  Role     : {row[2]}")
        print(f"  Status   : {row[3]}")
        print(f"  2FA      : {'ON' if row[4] else 'OFF'}")
        print("=" * 50)
        print("  Log in at:  http://localhost:5000/login")
        print("=" * 50)
    else:
        print("[ERROR] Could not verify update.")

if __name__ == '__main__':
    reset()