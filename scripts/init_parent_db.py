from utils.pg_wrapper import exe

def init_parent_tables():
    print("Expanding Database for Parent Communication...")
    
    commands = [
        # 1. Parent Contacts
        """
        CREATE TABLE IF NOT EXISTS parent_contacts (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            full_name TEXT NOT NULL,
            phone_primary VARCHAR(15) NOT NULL UNIQUE,
            phone_secondary VARCHAR(15),
            email TEXT,
            address TEXT,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW()
        )
        """,
        
        # 2. Student-Parent Mapping
        """
        CREATE TABLE IF NOT EXISTS student_parent_mapping (
            id SERIAL PRIMARY KEY,
            student_id INTEGER REFERENCES students(id) ON DELETE CASCADE,
            parent_id UUID REFERENCES parent_contacts(id) ON DELETE CASCADE,
            relationship_type VARCHAR(20) DEFAULT 'Father',
            is_primary_contact BOOLEAN DEFAULT TRUE,
            UNIQUE(student_id, parent_id)
        )
        """,
        
        # 3. Notification Preferences
        """
        CREATE TABLE IF NOT EXISTS notification_preferences (
            parent_id UUID REFERENCES parent_contacts(id) ON DELETE CASCADE,
            category VARCHAR(30) NOT NULL,
            is_enabled BOOLEAN DEFAULT TRUE,
            PRIMARY KEY (parent_id, category)
        )
        """,
        
        # 4. Add Category to Templates
        "ALTER TABLE sms_templates ADD COLUMN IF NOT EXISTS category VARCHAR(30) DEFAULT 'general'",
        "ALTER TABLE sms_templates ADD COLUMN IF NOT EXISTS language VARCHAR(5) DEFAULT 'en'"
    ]
    
    for cmd in commands:
        try:
            exe(cmd)
            print(f" [✓] Executed: {cmd[:40]}...")
        except Exception as e:
            print(f" [!] Error executing command: {e}")

    # Seed an Absent Notification Template
    try:
        exe("""
            INSERT INTO sms_templates (slug, body, category) 
            VALUES ('absent_alert', 'Dear Parent, {{student_name}} was marked absent on {{date}}. Please contact administration for any queries.', 'attendance')
            ON CONFLICT (slug) DO NOTHING
        """)
        print(" [✓] Seeded 'absent_alert' template.")
    except: pass

    print("Parent Database Infrastructure successfully initialized.")

if __name__ == "__main__":
    init_parent_tables()
