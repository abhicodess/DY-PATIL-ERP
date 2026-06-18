from flask import render_template, request, redirect, url_for, session, flash, current_app
from blueprints.auth import auth_bp
from services.student_service import StudentService
from services.faculty_service import FacultyService
from werkzeug.security import check_password_hash
from extensions import limiter
import os

student_service = StudentService()
faculty_service = FacultyService()

@auth_bp.route("/")
def index():
    if session.get("role"):
        r = session["role"]
        if r == "admin": return redirect(url_for('admin.dashboard'))
        if r == "faculty": return redirect(url_for('dashboard.faculty'))
        if r == "student": return redirect(url_for('dashboard.student'))
    return redirect(url_for('auth.login'))

@auth_bp.route("/login", methods=["GET", "POST"])
@auth_bp.route("/admin_login", methods=["GET", "POST"])
@auth_bp.route("/faculty_login", methods=["GET", "POST"])
@limiter.limit("10 per minute")
def login():
    if request.method == "POST":
        role = request.form.get("role", "").strip()
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        user_data = None
        
        if role == "admin":
            admin_hash = current_app.config.get("ADMIN_PASSWORD_HASH")
            if admin_hash and username == "admin" and check_password_hash(admin_hash, password):
                user_data = {"role": "admin", "name": "Administrator"}
            else:
                flash("Invalid admin credentials.", "danger")

        elif role == "faculty":
            faculty = faculty_service.verify_credentials(username, password)
            if faculty:
                user_data = {
                    "role": "faculty", 
                    "name": faculty.name, 
                    "faculty_id": faculty.id,
                    "department": faculty.department,
                    "must_change_password": getattr(faculty, "must_change_password", False)
                }
            else:
                flash("Invalid faculty credentials.", "danger")

        elif role == "student":
            student = student_service.verify_credentials(username, password)
            if student:
                user_data = {
                    "role": "student", 
                    "name": student.name, 
                    "student_id": student.id,
                    "student_roll": student.roll,
                    "student_branch": student.department,
                    "student_year": student.year,
                    "student_division": student.division,
                    "must_change_password": getattr(student, "must_change_password", False)
                }
            else:
                flash("Invalid student credentials.", "danger")

        if user_data:
            session.clear()
            for k, v in user_data.items():
                session[k] = v
            session.permanent = True
            
            # Generate JWT token embedded with tenant claims
            from flask_jwt_extended import create_access_token, set_access_cookies
            from utils.tenant_context import get_current_tenant
            
            tenant = get_current_tenant()
            user_id = user_data.get("student_id") or user_data.get("faculty_id") or "admin"
            additional_claims = {
                "tenant_id":     tenant['id'],
                "tenant_slug":   tenant['slug'],
                "tenant_schema": tenant['schema_name'],
                "role":          user_data['role']
            }
            access_token = create_access_token(
                identity=str(user_id),
                additional_claims=additional_claims
            )
            
            response = redirect(url_for('auth.index'))
            set_access_cookies(response, access_token)
            return response

    return render_template("common/login.html")

@auth_bp.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for('auth.login'))

@auth_bp.route("/forgot_password")
def forgot_password():
    return render_template("common/forgot_password.html")

@auth_bp.route("/reset_password", methods=["GET", "POST"])
@limiter.limit("5 per minute")
def reset_password():
    if request.method == "POST":
        new_pw = request.form.get("new_pw", "").strip()
        from utils.password_policy import validate_password
        is_valid, err_msg = validate_password(new_pw)
        if not is_valid:
            # Re-render with error
            return render_template("common/reset_password.html", 
                                   err=err_msg, 
                                   role=request.form.get("role"), 
                                   ident=request.form.get("identifier"))
            
        role = request.form.get("role", "").strip()
        ident = request.form.get("identifier", "").strip()
        
        # Verify OTP (mocked or database checked)
        from werkzeug.security import generate_password_hash
        hashed = generate_password_hash(new_pw, method='scrypt')
        from utils.pg_wrapper import exe
        if role == "student":
            exe("UPDATE students SET password=%s, must_change_password=FALSE WHERE roll=%s OR email=%s", (hashed, ident, ident))
        elif role == "faculty":
            exe("UPDATE faculty SET password=%s, must_change_password=FALSE WHERE phone=%s OR email=%s", (hashed, ident, ident))
            
        session.pop("must_change_password", None)
        flash("Password reset successfully.", "success")
        return redirect(url_for('auth.login'))
    return render_template("common/reset_password.html")

@auth_bp.route("/change_password", methods=["POST"])
@limiter.limit("5 per minute")
def change_password():
    from flask import jsonify
    from utils.password_policy import validate_password
    from utils.pg_wrapper import exe, qone
    from werkzeug.security import generate_password_hash, check_password_hash
    
    role = session.get("role")
    if not role:
        return jsonify({"success": False, "error": "Unauthorized"}), 401
        
    current_pw = request.form.get("current_password", "").strip()
    new_pw = request.form.get("new_password", "").strip()
    confirm_pw = request.form.get("confirm_password", "").strip()
    
    if new_pw != confirm_pw:
        return jsonify({"success": False, "error": "New passwords do not match."}), 400
        
    is_valid, err_msg = validate_password(new_pw)
    if not is_valid:
        return jsonify({"success": False, "error": err_msg}), 400
        
    if role == "admin":
        admin_hash = current_app.config.get("ADMIN_PASSWORD_HASH")
        if not check_password_hash(admin_hash, current_pw):
            return jsonify({"success": False, "error": "Invalid current password"}), 400
        new_hash = generate_password_hash(new_pw, method='scrypt')
        current_app.config["ADMIN_PASSWORD_HASH"] = new_hash
        try:
            with open(".env", "r") as f:
                lines = f.readlines()
            new_lines = []
            for line in lines:
                if line.strip().startswith("ADMIN_PASSWORD_HASH="):
                    new_lines.append(f"ADMIN_PASSWORD_HASH={new_hash.replace('$', '$$')}\n")
                elif line.strip().startswith("ADMIN_PASSWORD="):
                    new_lines.append(f"ADMIN_PASSWORD={new_pw}\n")
                else:
                    new_lines.append(line)
            with open(".env", "w") as f:
                f.writelines(new_lines)
        except Exception:
            pass
    elif role == "faculty":
        fid = session.get("faculty_id")
        row = qone("SELECT password FROM faculty WHERE id=%s", (fid,))
        if not row or not check_password_hash(row["password"], current_pw):
            return jsonify({"success": False, "error": "Invalid current password"}), 400
        exe("UPDATE faculty SET password=%s, must_change_password=FALSE WHERE id=%s", (generate_password_hash(new_pw, method='scrypt'), fid))
        session.pop("must_change_password", None)
    elif role == "student":
        sid = session.get("student_id")
        row = qone("SELECT password FROM students WHERE id=%s", (sid,))
        if not row or not check_password_hash(row["password"], current_pw):
            return jsonify({"success": False, "error": "Invalid current password"}), 400
        exe("UPDATE students SET password=%s, must_change_password=FALSE WHERE id=%s", (generate_password_hash(new_pw, method='scrypt'), sid))
        session.pop("must_change_password", None)
        
    return jsonify({"success": True, "message": "Password changed successfully."})

@auth_bp.before_app_request
def force_password_change():
    from flask import request, redirect, url_for, session
    if session.get("must_change_password"):
        allowed_endpoints = ("auth.logout", "auth.change_password", "auth.reset_password", "static")
        if request.endpoint and request.endpoint not in allowed_endpoints and not request.path.startswith("/api/"):
            return redirect(url_for("auth.reset_password"))

