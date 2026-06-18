from flask import render_template, request, redirect, url_for, flash, jsonify, send_file, session
import io
import pandas as pd
from blueprints.admissions import admissions_bp
from services.admissions_service import AdmissionsService
from blueprints.auth.decorators import admin_required

admissions_service = AdmissionsService()

# ── PUBLIC ROUTES (No login required) ───────────────────────────────────

@admissions_bp.route("/apply", methods=["GET", "POST"])
def apply():
    """Render the application form or handle form submission."""
    if request.method == "POST":
        try:
            form_data = request.form.to_dict()
            # Extract files
            documents = {}
            for doc_type in ['SSC_MARKSHEET', 'HSC_MARKSHEET', 'LEAVING_CERTIFICATE', 
                             'CASTE_CERTIFICATE', 'DOMICILE', 'PHOTO', 'SIGNATURE', 'OTHER']:
                file = request.files.get(doc_type)
                if file and file.filename != '':
                    documents[doc_type] = file

            app = admissions_service.submit_application(form_data, documents)
            flash(f"Application submitted successfully! Your token is: {app['token']}", "success")
            return render_template("admissions/success.html", token=app['token'])
        except Exception as e:
            flash(str(e), "error")
            return redirect(url_for('admissions.apply'))
            
    return render_template("admissions/apply.html")

@admissions_bp.route("/status/<token>", methods=["GET"])
def status(token):
    """Retrieve check status page for a given application token."""
    status_data = admissions_service.check_application_status(token)
    if not status_data:
        flash("Application token not found", "error")
        return render_template("admissions/status.html", not_found=True)
    return render_template("admissions/status.html", **status_data)

@admissions_bp.route("/documents/<token>", methods=["POST"])
def upload_single_doc(token):
    """Handle individual document upload for a given token."""
    app = admissions_service.repository.get_application_by_token(token)
    if not app:
        return jsonify(error="Application not found"), 404
        
    doc_type = request.form.get("document_type")
    file = request.files.get("file")
    if not doc_type or not file:
        return jsonify(error="Missing document type or file"), 400

    try:
        url = admissions_service.upload_document(app['id'], doc_type, file)
        return jsonify(success=True, url=url)
    except Exception as e:
        return jsonify(error=str(e)), 400


# ── ADMIN ROUTES (Login & Admin Role required) ──────────────────────────

@admissions_bp.route("/admin/dashboard", methods=["GET"])
@admin_required
def dashboard():
    """Admin dashboard view displaying and filtering all applications."""
    filters = {
        'department': request.args.get('department'),
        'category': request.args.get('category'),
        'status': request.args.get('status'),
        'date_start': request.args.get('date_start'),
        'date_end': request.args.get('date_end')
    }
    apps = admissions_service.repository.get_all_applications(filters)
    
    # Calculate stats
    total = len(apps)
    under_review = len([a for a in apps if a['status'] == 'UNDER_REVIEW'])
    merit_listed = len([a for a in apps if a['status'] == 'MERIT_LISTED'])
    selected = len([a for a in apps if a['status'] == 'SELECTED'])
    
    # Simple remaining seats calculation from seat_matrix
    from utils.pg_wrapper import qry
    seat_matrix = qry("SELECT SUM(available_seats) as total_avail FROM seat_matrix")
    seats_remaining = seat_matrix[0]['total_avail'] if seat_matrix and seat_matrix[0]['total_avail'] is not None else 0

    return render_template(
        "admissions/admin_dashboard.html",
        applications=apps,
        stats={
            'total': total,
            'under_review': under_review,
            'merit_listed': merit_listed,
            'selected': selected,
            'seats_remaining': seats_remaining
        },
        filters=filters
    )

@admissions_bp.route("/admin/<int:app_id>", methods=["GET"])
@admin_required
def admin_detail(app_id):
    """View details of a single application along with timeline and documents."""
    app = admissions_service.repository.get_application_by_id(app_id)
    if not app:
        flash("Application not found", "error")
        return redirect(url_for('admissions.dashboard'))

    docs = admissions_service.repository.get_documents_by_application(app_id)
    
    from utils.pg_wrapper import qry
    timeline = qry("SELECT * FROM application_timeline WHERE application_id = :app_id ORDER BY action_at DESC", {"app_id": app_id})

    return render_template(
        "admissions/admin_detail.html",
        application=app,
        documents=docs,
        timeline=timeline
    )

@admissions_bp.route("/admin/<int:app_id>/status", methods=["POST"])
@admin_required
def update_status(app_id):
    """Update application status along with optional remarks."""
    new_status = request.form.get("status")
    remarks = request.form.get("remarks", "")
    admin_id = session.get("user_id", 1)

    try:
        admissions_service.repository.update_application_status(app_id, new_status, remarks, admin_id)
        admissions_service.repository.log_timeline(
            application_id=app_id,
            action="STATUS_UPDATED",
            by=f"Admin (ID: {admin_id})",
            notes=f"Status changed to {new_status}. Remarks: {remarks}"
        )
        
        # Notify user of manual status change
        from tasks.notification_tasks import send_status_update
        send_status_update.delay(app_id, new_status)
        
        flash("Application status updated successfully", "success")
    except Exception as e:
        flash(str(e), "error")

    return redirect(url_for('admissions.admin_detail', app_id=app_id))

@admissions_bp.route("/admin/<int:app_id>/verify-doc", methods=["POST"])
@admin_required
def verify_doc(app_id):
    """Verify a specific document uploaded by an applicant."""
    doc_id = request.form.get("document_id")
    admin_id = session.get("user_id", 1)

    try:
        admissions_service.verify_document(int(doc_id), admin_id)
        flash("Document verified successfully", "success")
    except Exception as e:
        flash(str(e), "error")

    return redirect(url_for('admissions.admin_detail', app_id=app_id))

@admissions_bp.route("/admin/merit-list", methods=["GET", "POST"])
@admin_required
def merit_list():
    """View and generate provisional merit list per department & category."""
    from utils.pg_wrapper import qry
    
    dept = request.args.get("department", "AIML")
    cat = request.args.get("category", "OPEN")
    year = request.args.get("academic_year", "2026")
    admin_id = session.get("user_id", 1)

    if request.method == "POST":
        # Handle generation request
        dept = request.form.get("department", dept)
        cat = request.form.get("category", cat)
        year = request.form.get("academic_year", year)
        
        admissions_service.generate_merit_list(dept, cat, year, admin_id)
        flash(f"Provisional Merit List generated for {dept} ({cat})", "success")
        return redirect(url_for('admissions.merit_list', department=dept, category=cat, academic_year=year))

    # Retrieve current merit list
    ml_entries = qry(
        """
        SELECT ml.*, app.applicant_name, app.token 
        FROM merit_lists ml
        JOIN applications app ON ml.application_id = app.id
        WHERE ml.department = :dept AND ml.category = :cat AND ml.academic_year = :year
        ORDER BY ml.rank ASC
        """,
        {"dept": dept, "cat": cat, "year": year}
    )

    # Fetch seat matrix info
    seat_info = admissions_service.repository.get_seat_matrix_entry(dept, cat, year)

    return render_template(
        "admissions/merit_list.html",
        merit_list=ml_entries,
        selected_department=dept,
        selected_category=cat,
        selected_year=year,
        seat_info=seat_info
    )

@admissions_bp.route("/admin/merit-list/finalize", methods=["POST"])
@admin_required
def finalize_merit_list_route():
    """Finalize the provisional merit list, moving candidates to selected/waitlisted."""
    dept = request.form.get("department")
    cat = request.form.get("category")
    year = request.form.get("academic_year")
    admin_id = session.get("user_id", 1)

    try:
        success = admissions_service.finalize_merit_list(dept, cat, year, admin_id)
        if success:
            flash(f"Merit list finalized and offer letters dispatched for {dept} ({cat}).", "success")
        else:
            flash("No provisional merit list found to finalize.", "warning")
    except Exception as e:
        flash(str(e), "error")

    return redirect(url_for('admissions.merit_list', department=dept, category=cat, academic_year=year))

@admissions_bp.route("/admin/seat-matrix", methods=["GET"])
@admin_required
def seat_matrix():
    """Display the seats layout matrix for the selected academic year."""
    year = request.args.get("academic_year", "2026")
    matrix = admissions_service.get_seat_matrix(year)
    return render_template("admissions/seat_matrix.html", seat_matrix=matrix, selected_year=year)

@admissions_bp.route("/admin/export", methods=["GET"])
@admin_required
def export_applications():
    """Export the list of applications matching filters to an Excel sheet."""
    filters = {
        'department': request.args.get('department'),
        'category': request.args.get('category'),
        'status': request.args.get('status'),
        'date_start': request.args.get('date_start'),
        'date_end': request.args.get('date_end')
    }
    apps = admissions_service.repository.get_all_applications(filters)
    
    data_list = []
    for row in apps:
        data_list.append({
            "Token": row['token'],
            "Name": row['applicant_name'],
            "Email": row['applicant_email'],
            "Phone": row['applicant_phone'],
            "DOB": str(row['date_of_birth']),
            "Gender": row['gender'],
            "Category": row['category'],
            "Domicile State": row['domicile_state'],
            "Applied Department": row['applied_department'],
            "Applied Year": row['applied_year'],
            "Status": row['status'],
            "Merit Score": row['merit_score'],
            "Rank": row['rank_in_department'],
            "Submitted At": str(row['submitted_at'])
        })
        
    df = pd.DataFrame(data_list)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Applications')
    output.seek(0)
    
    return send_file(
        output,
        as_attachment=True,
        download_name="admissions_applications.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
