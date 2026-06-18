import psycopg2
from pg_wrapper import get_db, exe

def upgrade():
    print("Upgrading database schema...")
    
    # 1. Add student fields
    cols = [
        ('contact_number', 'TEXT'),
        ('parent_contact', 'TEXT'),
        ('dob', 'DATE'),
        ('gender', 'TEXT'),
        ('address', 'TEXT'),
        ('admission_year', 'INTEGER')
    ]
    
    conn = get_db()
    for col, ctype in cols:
        try:
            conn.execute(f"ALTER TABLE students ADD COLUMN {col} {ctype}")
            conn.commit()
            print(f"Added column {col} to students")
        except psycopg2.errors.DuplicateColumn:
            conn.rollback()
            print(f"Column {col} already exists")
        except Exception as e:
            conn.rollback()
            print(f"Error adding {col}: {e}")
            
    # 2. Add qr_sessions context (latitude, longitude) if not exists
    try:
        conn.execute("ALTER TABLE qr_sessions ADD COLUMN latitude FLOAT")
        conn.execute("ALTER TABLE qr_sessions ADD COLUMN longitude FLOAT")
        conn.commit()
    except Exception:
        conn.rollback()

    conn.close()
    print("Upgrade done.")

if __name__ == '__main__':
    upgrade()
