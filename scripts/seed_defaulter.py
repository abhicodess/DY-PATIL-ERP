from utils.pg_wrapper import exe

def seed_defaulter_template():
    print("Seeding Defaulter Alert Template...")
    exe("""
        INSERT INTO sms_templates (slug, body, category) 
        VALUES ('defaulter_alert', 'Urgent: Dear Parent, {{student_name}} has low attendance ({{percentage}}%%). Please ensure regular attendance to avoid academic penalties.', 'attendance') 
        ON CONFLICT (slug) DO NOTHING
    """)
    print("[✓] Template seeded successfully.")

if __name__ == "__main__":
    seed_defaulter_template()
