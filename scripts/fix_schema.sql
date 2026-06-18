-- Fix missing columns in students table
ALTER TABLE students ADD COLUMN IF NOT EXISTS prn TEXT;
ALTER TABLE students ADD COLUMN IF NOT EXISTS contact_number TEXT;
ALTER TABLE students ADD COLUMN IF NOT EXISTS parent_contact TEXT;
ALTER TABLE students ADD COLUMN IF NOT EXISTS dob DATE;
ALTER TABLE students ADD COLUMN IF NOT EXISTS gender TEXT;
ALTER TABLE students ADD COLUMN IF NOT EXISTS address TEXT;
ALTER TABLE students ADD COLUMN IF NOT EXISTS admission_year INTEGER;
ALTER TABLE students ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;

-- Fix missing columns in faculty table
ALTER TABLE faculty ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;

-- Ensure audit_logs and notifications exist
CREATE TABLE IF NOT EXISTS audit_logs (
    id SERIAL PRIMARY KEY,
    action TEXT,
    details TEXT,
    role TEXT,
    user_id INTEGER,
    ip_addr TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS notifications (
    id SERIAL PRIMARY KEY,
    title TEXT,
    message TEXT,
    role_target TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
