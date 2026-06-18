"""
Enterprise Route Registry & Governance
Centralized management of ERP endpoints to prevent BuildError and hardcoding chaos.
"""

from flask import url_for, current_app, redirect, flash, request
import logging

# Feature Flags (To enable/disable features without crashing)
FEATURE_FLAGS = {
    "AI_INSIGHTS": True,
    "EXPORT_ANALYTICS": True,
    "ADVANCED_REPORTS": False, # Coming Soon
}

# Central Registry of all feature-linked endpoints
ROUTES = {
    # AUTH
    "login": {"endpoint": "login", "roles": []},
    "logout": {"endpoint": "logout", "roles": []},

    # ADMIN DASHBOARD & CORE
    "admin_dashboard": {"endpoint": "admin_dashboard", "roles": ["admin"]},
    "admin_profile": {"endpoint": "admin_profile", "roles": ["admin"]},
    "admin_audit_logs": {"endpoint": "features.admin_audit_logs", "roles": ["admin"]},
    "admin_notifications": {"endpoint": "features.admin_notifications", "roles": ["admin"]},
    "admin_backup": {"endpoint": "features.admin_backup", "roles": ["admin"]},

    # INTEL & ANALYTICS
    "admin_attendance_intelligence": {"endpoint": "admin_intel.admin_attendance_intelligence", "roles": ["admin"], "flag": "AI_INSIGHTS"},
    "admin_session_detail": {"endpoint": "admin_intel.admin_session_detail", "roles": ["admin"]},
    "audit_session_detail": {"endpoint": "admin_intel.admin_session_detail", "roles": ["admin"]},
    "faculty_logs": {"endpoint": "admin_intel.admin_faculty_logs", "roles": ["admin"]},
    "admin_faculty_logs": {"endpoint": "admin_intel.admin_faculty_logs", "roles": ["admin"]},
    
    # ENTITY MANAGEMENT
    "students": {"endpoint": "students", "roles": ["admin"]},
    "faculty": {"endpoint": "faculty", "roles": ["admin"]},
    "subjects": {"endpoint": "subjects", "roles": ["admin"]},
    "timetable": {"endpoint": "timetable", "roles": ["admin"]},
    "timetable_v2": {"endpoint": "timetable_v2.timetable_view", "roles": ["admin"]},

    # ATTENDANCE (ADMIN/FACULTY)
    "attendance_roll_call": {"endpoint": "attendance_roll_call", "roles": ["admin", "faculty"]},
    "view_attendance": {"endpoint": "view_attendance", "roles": ["admin", "faculty"]},
    "attendance_report": {"endpoint": "attendance_report", "roles": ["admin", "faculty"]},
    "attendance_analytics": {"endpoint": "attendance_analytics", "roles": ["admin"]},
    "attendance_export": {"endpoint": "attendance_export", "roles": ["admin"]},
    "student_attendance_profile": {"endpoint": "student_attendance_profile", "roles": ["admin", "faculty"]},

    # FACULTY DASHBOARD & SERVICES
    "faculty_dashboard": {"endpoint": "faculty_dashboard", "roles": ["faculty"]},
    "faculty_attendance": {"endpoint": "faculty_att.attendance_portal", "roles": ["faculty"]},
    "faculty_sessions": {"endpoint": "faculty_att.session_history", "roles": ["faculty"]},
    "faculty_students": {"endpoint": "faculty_att.my_students", "roles": ["faculty"]},
    "faculty_marks": {"endpoint": "faculty_marks", "roles": ["faculty"]},
    "faculty_timetable": {"endpoint": "faculty_timetable", "roles": ["faculty"]},
    "faculty_profile": {"endpoint": "faculty_profile", "roles": ["faculty"]},

    # STUDENT
    "student_dashboard": {"endpoint": "student_dashboard", "roles": ["student"]},
    "student_attendance": {"endpoint": "student_attendance", "roles": ["student"]},
    "student_profile": {"endpoint": "student_profile", "roles": ["student"]},
}

def get_route(key, **kwargs):
    """
    Safely resolves a route key to a URL with Feature Flag checks.
    """
    route_cfg = ROUTES.get(key)
    
    # If it's a direct endpoint string or not in registry, try as is
    if not route_cfg:
        endpoint = key
    else:
        # Check Feature Flag
        flag = route_cfg.get("flag")
        if flag and not FEATURE_FLAGS.get(flag, True):
             return f"javascript:alert('Feature {key} is Coming Soon!');"
        
        endpoint = route_cfg["endpoint"]

    try:
        return url_for(endpoint, **kwargs)
    except Exception as e:
        logging.getLogger(__name__).error(f"Route resolution failure: {key} -> {endpoint}. Error: {e}")
        return f"/route-not-found?endpoint={key}"

def init_app(app):
    """Integrate registry into Flask app context."""
    @app.context_processor
    def inject_routes():
        return dict(
            route=get_route,
            R=ROUTES # Raw access to registry
        )

    # Global Fallback for missing routes
    @app.route("/missing-route")
    def route_not_found():
        endpoint = request.args.get("endpoint", "unknown")
        flash(f"The feature '{endpoint}' is currently under development or temporarily unavailable.", "info")
        return redirect(url_for('index'))
