-- Complete Database Schema for Construction Website System

-- Users Table with Soft Delete and 2FA Support
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    phone TEXT,
    password_hash TEXT NOT NULL,
    address TEXT,
    role TEXT DEFAULT 'Customer',  -- SuperAdmin, ProjectManager, Customer
    account_status TEXT DEFAULT 'Active',  -- Active, Suspended, Deleted
    two_factor_enabled INTEGER DEFAULT 0,  -- 0 = off, 1 = on
    two_factor_secret TEXT,
    reset_token TEXT,
    reset_token_expiry TIMESTAMP,
    deleted_at TIMESTAMP,  -- For soft delete tracking
    last_login TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Activity Logs Table
CREATE TABLE IF NOT EXISTS activity_logs (
    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    user_email TEXT,
    action TEXT NOT NULL,
    details TEXT,
    ip_address TEXT,
    user_agent TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

-- Services Table
CREATE TABLE IF NOT EXISTS services (
    service_id INTEGER PRIMARY KEY AUTOINCREMENT,
    service_name TEXT NOT NULL,
    description TEXT,
    image_path TEXT,
    category TEXT,
    is_active INTEGER DEFAULT 1,
    created_by INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (created_by) REFERENCES users(user_id)
);

-- Projects Table (Orders/Quotes)
CREATE TABLE IF NOT EXISTS projects (
    project_id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER NOT NULL,
    service_id INTEGER NOT NULL,
    project_description TEXT,
    budget DECIMAL(10,2),
    location TEXT,
    status TEXT DEFAULT 'Pending',
    assigned_to INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES users(user_id),
    FOREIGN KEY (service_id) REFERENCES services(service_id),
    FOREIGN KEY (assigned_to) REFERENCES users(user_id)
);

-- Project Updates Table
CREATE TABLE IF NOT EXISTS project_updates (
    update_id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    update_description TEXT,
    image_path TEXT,
    created_by INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects(project_id),
    FOREIGN KEY (created_by) REFERENCES users(user_id)
);

-- Payments Table
CREATE TABLE IF NOT EXISTS payments (
    payment_id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    payment_method TEXT,
    payment_status TEXT DEFAULT 'Pending',
    amount DECIMAL(10,2),
    transaction_id TEXT,
    payer_email TEXT,
    bank_account_name TEXT,
    bank_account_number TEXT,
    verified_by INTEGER,
    verified_at TIMESTAMP,
    admin_notes TEXT,
    payment_date TIMESTAMP,
    payment_proof_path TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects(project_id)
);

-- Gallery Table
CREATE TABLE IF NOT EXISTS gallery (
    gallery_id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT,
    image_path TEXT NOT NULL,
    category TEXT,
    uploaded_by INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (uploaded_by) REFERENCES users(user_id)
);

-- Messages Table
CREATE TABLE IF NOT EXISTS messages (
    message_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL,
    subject TEXT,
    message TEXT NOT NULL,
    is_read INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Backup Logs Table
CREATE TABLE IF NOT EXISTS backup_logs (
    backup_id INTEGER PRIMARY KEY AUTOINCREMENT,
    backup_filename TEXT NOT NULL,
    backup_size INTEGER,
    backup_type TEXT,  -- full, database, uploads
    created_by INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (created_by) REFERENCES users(user_id)
);


-- System Settings Table (add to existing schema.sql)
CREATE TABLE IF NOT EXISTS system_settings (
    setting_key TEXT PRIMARY KEY,
    setting_value TEXT,
    setting_type TEXT DEFAULT 'string',  -- string, number, boolean, json
    description TEXT,
    updated_by INTEGER,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (updated_by) REFERENCES users(user_id)
);

CREATE TABLE IF NOT EXISTS two_fa_codes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    code TEXT NOT NULL,
    used INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS security_alerts (
    alert_id INTEGER PRIMARY KEY AUTOINCREMENT,
    severity TEXT NOT NULL DEFAULT 'Low',
    rule_name TEXT NOT NULL,
    description TEXT NOT NULL,
    source_ip TEXT,
    user_id INTEGER,
    status TEXT DEFAULT 'Open',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP,
    resolved_by INTEGER,
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    FOREIGN KEY (resolved_by) REFERENCES users(user_id)
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);
CREATE INDEX IF NOT EXISTS idx_users_status ON users(account_status);
CREATE INDEX IF NOT EXISTS idx_projects_customer ON projects(customer_id);
CREATE INDEX IF NOT EXISTS idx_projects_status ON projects(status);
CREATE INDEX IF NOT EXISTS idx_activity_logs_user ON activity_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_activity_logs_timestamp ON activity_logs(timestamp);
CREATE INDEX IF NOT EXISTS idx_two_fa_codes_user ON two_fa_codes(user_id);
CREATE INDEX IF NOT EXISTS idx_security_alerts_status ON security_alerts(status);

-- Insert default Super Admin (password: Admin@123)
INSERT OR IGNORE INTO users (name, email, phone, password_hash, role, account_status, two_factor_enabled)
VALUES ('Super Admin', 'aldanehutchinson5@gmail.com', '+1234567890', 
        'pbkdf2:sha256:600000$codexsalt$8c740571300d4cc57925fd098f579c2200e95af2c66a444edd20358177ccbc91', 
        'SuperAdmin', 'Active', 0);

-- Insert sample services
INSERT OR IGNORE INTO services (service_id, service_name, description, category, is_active) VALUES
(1, 'Carpentry', 'Professional carpentry services including furniture, cabinets, and woodwork', 'Carpentry', 1),
(2, 'Masonry', 'Brick, block, stone work for walls, foundations, and structures', 'Masonry', 1),
(3, 'Plumbing', 'Complete plumbing installation and repair services', 'Plumbing', 1),
(4, 'Electrical', 'Electrical wiring, installation, and maintenance', 'Electrical', 1),
(5, 'Painting', 'Interior and exterior painting services', 'Painting', 1),
(6, 'Tiling', 'Floor and wall tiling for bathrooms, kitchens, and more', 'Tiling', 1);
