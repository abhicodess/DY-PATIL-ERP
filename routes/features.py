"""
routes/features.py — Extended features (Audit, Notifications, Backup)
"""
from flask import Blueprint, render_template, request, redirect, session, jsonify, send_file, current_app
import psycopg2
import os, datetime
from utils.pg_wrapper import exe, qry, qone

features_bp = Blueprint("features", __name__)
DATABASE = "college.db" # match legacy if needed

# ----------------- 1. AUDIT LOGS -----------------
def _ensure_audit_logs_table():
    exe("""
        CREATE TABLE IF NOT EXISTS audit_logs (
            id SERIAL PRIMARY KEY,
            action TEXT,
            details TEXT,
            role TEXT,
            user_id INTEGER,
            ip_addr TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)


def _ensure_notifications_table():
    exe("""
        CREATE TABLE IF NOT EXISTS notifications (
            id SERIAL PRIMARY KEY,
            title TEXT,
            message TEXT,
            role_target TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)


def log_audit(action, details):
    role = session.get("role", "guest")
    user_id = session.get(f"{role}_id", 0)
    ip_addr = request.remote_addr
    try:
        _ensure_audit_logs_table()
        exe("INSERT INTO audit_logs (action, details, role, user_id, ip_addr) VALUES (%s, %s, %s, %s, %s)", 
            (action, details, role, user_id, ip_addr))
    except Exception as e:
        current_app.logger.error(f"Audit log failed: {e}")

@features_bp.route("/admin_audit_logs")
def admin_audit_logs():
    if session.get("role") != "admin": return redirect("/")
    _ensure_audit_logs_table()
    logs = qry("SELECT * FROM audit_logs ORDER BY id DESC LIMIT 200")
    return render_template("common/audit_logs.html", logs=logs)


# ----------------- 2. NOTIFICATIONS SYSTEM -----------------
@features_bp.route("/api/notifications")
def api_notifications():
    role = session.get("role") or "guest"
    _ensure_notifications_table()
    rows = qry("SELECT * FROM notifications WHERE role_target=%s OR role_target='all' ORDER BY id DESC LIMIT 10", (role,))
    return jsonify([dict(r) for r in rows])

@features_bp.route("/admin_notifications", methods=["GET", "POST"])
def admin_notifications():
    if session.get("role") != "admin": return redirect("/")
    
    if request.method == "POST":
        title = request.form.get("title")
        message = request.form.get("message")
        role_target = request.form.get("role_target", "all")
        _ensure_notifications_table()
        exe("INSERT INTO notifications (title, message, role_target) VALUES (%s, %s, %s)", 
            (title, message, role_target))
        log_audit("Publish Notification", f"Title: {title}")
        return redirect("/admin_notifications")
    
    _ensure_notifications_table()
    logs = qry("SELECT * FROM notifications ORDER BY id DESC LIMIT 100")
    return render_template("admin/admin_notifications.html", notifications=logs)

@features_bp.route("/delete_notification/<int:nid>", methods=["POST"])
def delete_notification(nid):
    if session.get("role") != "admin": return jsonify({"error": "Unauthorized"}), 403
    exe("DELETE FROM notifications WHERE id=%s", (nid,))
    return redirect("/admin_notifications")


# ----------------- 3. BACKUP SYSTEM -----------------
@features_bp.route("/admin_backup")
def admin_backup():
    if session.get("role") != "admin": return redirect("/")
    # Keep legacy SQLite backup path if the file still exists locally.
    if not os.path.exists(DATABASE):
        return "Backup file not available (running on PostgreSQL)."
    log_audit("Database Backup", "Downloaded college.db")
    return send_file(DATABASE, as_attachment=True, download_name=f"backup_college_erp_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.db")


# ----------------- 4. API ENDPOINTS -----------------
@features_bp.route("/api/v1/stats")
def api_v1_stats():
    students_count = qone("SELECT count(*) as c FROM students")["c"]
    faculty_count = qone("SELECT count(*) as c FROM faculty")["c"]
    return jsonify({
        "status": "success",
        "timestamp": datetime.datetime.now().isoformat(),
        "metrics": {
            "total_students": students_count,
            "total_faculty": faculty_count
        }
    })

@features_bp.route("/api/v1/departments")
def api_v1_departments():
    depts = [dict(r) for r in qry("SELECT DISTINCT department FROM students WHERE department IS NOT NULL")]
    return jsonify({"status": "success", "data": depts})


# RESULT PUBLISH CONTROL IS ALREADY IN app.py 
# SMART DASHBOARD WILL BE IMPLEMENTED BY OVERRIDING index.html or admin.html and adding these links.
