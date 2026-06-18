import os

MINIMAL_SIDEBAR = '''{% block sidebar_nav %}
<div class="sb-sec">Overview</div>
<a href="/student_dashboard" class="sb-link {% if request.path == '/student_dashboard' %}active{% endif %}"><i class="fas fa-gauge-high"></i> Dashboard</a>
<div class="sb-sec">Academic</div>
<a href="/student_attendance" class="sb-link {% if request.path == '/student_attendance' or request.path == '/student_attendance_dashboard' %}active{% endif %}"><i class="fas fa-calendar-check"></i> Attendance</a>
<a href="/student_marks" class="sb-link {% if request.path == '/student_marks' %}active{% endif %}"><i class="fas fa-star-half-stroke"></i> Marks</a>
<a href="/student_timetable" class="sb-link {% if request.path == '/student_timetable' %}active{% endif %}"><i class="fas fa-table-cells"></i> Timetable</a>
<div class="sb-sec">Account</div>
<a href="/student_profile" class="sb-link {% if request.path == '/student_profile' %}active{% endif %}"><i class="fas fa-user-circle"></i> Profile</a>
{% endblock %}
'''

for filename in ['student_attendance.html', 'student_attendance_dashboard.html']:
    filepath = os.path.join('templates', filename)
    if os.path.exists(filepath):
        with open(filepath, 'r+', encoding='utf-8') as f:
            content = f.read()
            if '{% block sidebar_nav %}' not in content:
                # Insert right after the first {% extends ... %}
                first_line_end = content.find('}') + 1
                if first_line_end > 0:
                    new_content = content[:first_line_end] + '\n' + MINIMAL_SIDEBAR + content[first_line_end:]
                    f.seek(0)
                    f.write(new_content)
                    f.truncate()
                    print('Added to', filename)
