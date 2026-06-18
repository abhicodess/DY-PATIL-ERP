import os
import re

MINIMAL_SIDEBAR = '''{% block sidebar_nav %}
<div class="sb-sec">Overview</div>
<a href="/student_dashboard" class="sb-link {% if request.path == '/student_dashboard' %}active{% endif %}"><i class="fas fa-gauge-high"></i> Dashboard</a>
<div class="sb-sec">Academic</div>
<a href="/student_attendance" class="sb-link {% if request.path == '/student_attendance' or request.path == '/student_attendance_dashboard' %}active{% endif %}"><i class="fas fa-calendar-check"></i> Attendance</a>
<a href="/student_marks" class="sb-link {% if request.path == '/student_marks' %}active{% endif %}"><i class="fas fa-star-half-stroke"></i> Marks</a>
<a href="/student_timetable" class="sb-link {% if request.path == '/student_timetable' %}active{% endif %}"><i class="fas fa-table-cells"></i> Timetable</a>
<div class="sb-sec">Account</div>
<a href="/student_profile" class="sb-link {% if request.path == '/student_profile' %}active{% endif %}"><i class="fas fa-user-circle"></i> Profile</a>
{% endblock %}'''

directory = 'templates'
count = 0
for filename in os.listdir(directory):
    if filename.startswith('student_') and filename.endswith('.html'):
        filepath = os.path.join(directory, filename)
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Regex to replace everything between {% block sidebar_nav %} and {% endblock %}
        new_content = re.sub(
            r'\{% block sidebar_nav %\}.*?\{% endblock %\}',
            MINIMAL_SIDEBAR,
            content,
            flags=re.DOTALL
        )
        
        if new_content != content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print('Updated', filename)
            count += 1
print(f"Total updated: {count}")
