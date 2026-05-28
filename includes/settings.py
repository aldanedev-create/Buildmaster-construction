from config.config import Config
from includes.db import execute, query_one


def get_setting(key, default=None):
    row = query_one("SELECT setting_value FROM system_settings WHERE setting_key = ?", [key])
    return row["setting_value"] if row else default


def set_setting(key, value, user_id=None):
    execute(
        """
        INSERT INTO system_settings (setting_key, setting_value, updated_by, updated_at)
        VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(setting_key) DO UPDATE SET
            setting_value = excluded.setting_value,
            updated_by = excluded.updated_by,
            updated_at = CURRENT_TIMESTAMP
        """,
        [key, str(value), user_id],
    )


def is_maintenance_mode():
    value = get_setting("maintenance_mode")
    if value is None:
        return Config.MAINTENANCE_MODE
    return str(value).lower() in ("1", "true", "yes", "on")


def get_maintenance_message():
    return get_setting("maintenance_message", Config.MAINTENANCE_MESSAGE)

