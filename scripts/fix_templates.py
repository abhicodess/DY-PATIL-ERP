import os
import re

MAPPINGS = {
    "admin_attendance_intelligence": "admin_intel.admin_attendance_intelligence",
    "admin_faculty_sessions": "faculty_logs",
    "admin_student_attendance": "student_attendance_profile",
    "admin_session_detail": "admin_intel.admin_session_detail"
}

def fix_templates(root_dir):
    for root, dirs, files in os.walk(root_dir):
        for file in files:
            if file.endswith('.html'):
                path = os.path.join(root, file)
                changed = False
                with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                new_content = content
                for old, new in MAPPINGS.items():
                    # Match url_for('old' or url_for("old"
                    pattern = rf"url_for\(['\"]{old}['\"]"
                    replacement = f"url_for('{new}'"
                    if re.search(pattern, new_content):
                        new_content = re.sub(pattern, replacement, new_content)
                        changed = True
                
                if changed:
                    with open(path, 'w', encoding='utf-8') as f:
                        f.write(new_content)
                    print(f"Fixed: {path}")

if __name__ == "__main__":
    fix_templates(r"d:\DY PATIL ERP\templates")
