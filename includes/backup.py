import os
import zipfile
from datetime import datetime

from config.config import Config
from includes.db import execute, query_all


class BackupManager:
    def __init__(self):
        self.backup_dir = Config.DATABASE_BACKUP_PATH
        os.makedirs(self.backup_dir, exist_ok=True)

    def get_backup_list(self):
        return query_all("SELECT * FROM backup_logs ORDER BY created_at DESC")

    def create_backup(self, user_id, backup_type='full'):
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"backup_{backup_type}_{timestamp}.zip"
        path = os.path.join(self.backup_dir, filename)

        with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as archive:
            if os.path.exists(Config.DATABASE_PATH):
                archive.write(Config.DATABASE_PATH, 'database/construction.db')
            if backup_type in ('full', 'uploads') and os.path.isdir(Config.UPLOAD_FOLDER):
                for root, _, files in os.walk(Config.UPLOAD_FOLDER):
                    for file_name in files:
                        file_path = os.path.join(root, file_name)
                        archive.write(file_path, os.path.join('uploads', os.path.relpath(file_path, Config.UPLOAD_FOLDER)))

        size = os.path.getsize(path)
        execute(
            "INSERT INTO backup_logs (backup_filename, backup_size, backup_type, created_by) VALUES (?, ?, ?, ?)",
            [filename, size, backup_type, user_id],
        )
        return filename

    def restore_backup(self, filename):
        return False, "Automatic restore is disabled. Download the backup and restore it manually."


backup_manager = BackupManager()

