from utils.pg_wrapper import exe

def init_sms_tables():
    print("Initializing SMS tables in PostgreSQL...")
    
    # 1. Extensions
    try:
        exe('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
        print(" [✓] UUID Extension ready")
    except Exception as e:
        print(f" [!] Note: Could not ensure uuid-ossp (might lack superuser): {e}")

    # 2. Enums
    # In Postgres, we check if they exist first or use a DO block
    enum_check = """
    DO $$ 
    BEGIN
        IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'sms_status') THEN
            CREATE TYPE sms_status AS ENUM ('queued', 'sending', 'delivered', 'failed', 'retrying');
        END IF;
        IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'sms_provider_type') THEN
            CREATE TYPE sms_provider_type AS ENUM ('twilio', 'fast2sms', 'msg91', 'aws');
        END IF;
    END $$;
    """
    try:
        exe(enum_check)
        print(" [✓] Enum types ready")
    except Exception as e:
        print(f" [!] Note: Enum types might already exist or need manual check: {e}")

    # 3. Tables
    tables = [
        """
        CREATE TABLE IF NOT EXISTS sms_logs (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            recipient VARCHAR(15) NOT NULL,
            message TEXT NOT NULL,
            provider TEXT NOT NULL,
            status TEXT DEFAULT 'queued',
            provider_ref VARCHAR(100),
            meta_data JSONB DEFAULT '{}',
            retry_count INT DEFAULT 0,
            error_log TEXT,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW()
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS sms_templates (
            id SERIAL PRIMARY KEY,
            slug VARCHAR(50) UNIQUE NOT NULL,
            body TEXT NOT NULL,
            placeholders JSONB,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS otp_verifications (
            id SERIAL PRIMARY KEY,
            phone VARCHAR(15) NOT NULL,
            otp_code VARCHAR(10) NOT NULL,
            expires_at TIMESTAMPTZ NOT NULL,
            is_verified BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
        """
    ]
    
    for sql in tables:
        exe(sql)
    
    # 4. Insert a sample template for testing
    try:
        exe("INSERT INTO sms_templates (slug, body) VALUES ('welcome_msg', 'Hello {{name}}, welcome to the ERP portal!') ON CONFLICT DO NOTHING")
    except: pass

    print("Successfully initialized all SMS tables.")

if __name__ == "__main__":
    init_sms_tables()
