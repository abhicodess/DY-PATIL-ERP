import os
import json
from datetime import datetime
from flask import Blueprint, request, send_file
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt

from services.report_service import ReportService, ReportValidationError, REPORT_REGISTRY
from utils.pg_wrapper import qone, exe
from utils.api_response import success_response, error_response

reports_bp = Blueprint('reports_api', __name__)

def verify_report_access(row, user_id, role):
    """
    Helper to verify if a user has access to a specific report record.
    Admins can access everything.
    """
    if role == "admin":
        return True
        
    # Parse filters JSONB to read meta creator info
    try:
        filters_dict = json.loads(row["filters"]) if isinstance(row["filters"], str) else row["filters"]
        meta = filters_dict.get("_meta", {})
    except Exception:
        meta = {}
        
    creator_id = str(meta.get("user_id", ""))
    creator_role = meta.get("role", "")
    
    if role == "student":
        # Students can only access reports linked to their student ID
        db_created_by = str(row["created_by"]) if row["created_by"] is not None else ""
        return db_created_by == str(user_id)
        
    if role == "faculty":
        # Faculty can only access reports they personally created
        return creator_role == "faculty" and creator_id == str(user_id)
        
    return False

@reports_bp.route("/generate", methods=["POST"])
@jwt_required()
def generate_report():
    """
    Queues a report generation job and returns 202 Accepted.
    """
    user_id = get_jwt_identity()
    claims = get_jwt()
    role = claims.get("role")
    name = claims.get("name", "User")
    dept = claims.get("department")
    
    requested_by = {
        "id": int(user_id),
        "role": role,
        "name": name,
        "department": dept
    }
    
    body = request.get_json() or {}
    report_type = body.get("report_type")
    fmt = body.get("format")
    filters = body.get("filters", {})
    
    try:
        job_id = ReportService.generate(report_type, fmt, filters, requested_by)
        
        # Look up estimated time
        registry_info = REPORT_REGISTRY.get(report_type, {})
        est_seconds = registry_info.get("estimated_seconds", 30)
        
        return success_response(
            data={
                "job_id": job_id,
                "status": "queued",
                "estimated_seconds": est_seconds
            },
            message="Report generation job accepted and queued.",
            status=202
        )
    except ReportValidationError as val_err:
        return error_response(
            message=str(val_err),
            code="VALIDATION_ERROR",
            status=422
        )
    except Exception as e:
        return error_response(
            message=f"Internal error starting report: {str(e)}",
            code="INTERNAL_SERVER_ERROR",
            status=500
        )

@reports_bp.route("/status/<job_id>", methods=["GET"])
@jwt_required()
def get_job_status(job_id):
    """
    Polls the status of a queued report job.
    """
    user_id = get_jwt_identity()
    role = get_jwt().get("role")
    
    # Retrieve ownership metadata from DB
    row = qone("SELECT created_by, filters FROM reports WHERE job_id = %s", (job_id,))
    if not row:
        return error_response("Report job not found", "NOT_FOUND", 404)
        
    if not verify_report_access(row, user_id, role):
        return error_response("Access denied for this report job", "FORBIDDEN", 403)
        
    status_info = ReportService.get_status(job_id)
    if not status_info:
        return error_response("Report status mapping failed", "NOT_FOUND", 404)
        
    return success_response(status_info, "Job status retrieved successfully.")

@reports_bp.route("/download/<job_id>", methods=["GET"])
@jwt_required()
def download_report(job_id):
    """
    Downloads a completed PDF or Excel report file.
    """
    user_id = get_jwt_identity()
    role = get_jwt().get("role")
    
    row = qone(
        "SELECT created_by, filters, format, file_path, status, expires_at FROM reports WHERE job_id = %s",
        (job_id,)
    )
    if not row:
        return error_response("Report job not found", "NOT_FOUND", 404)
        
    if not verify_report_access(row, user_id, role):
        return error_response("Access denied to download this report", "FORBIDDEN", 403)
        
    if row["status"] != "done":
        return error_response(
            message=f"Report is not ready. Current status: '{row['status']}'",
            code="REPORT_NOT_READY",
            status=400
        )
        
    file_path = row["file_path"]
    if not file_path or not os.path.exists(file_path):
        return error_response("Report file does not exist on disk", "NOT_FOUND", 404)
        
    if row["expires_at"] < datetime.now():
        return error_response(
            message="This report file has expired (24h limit) and is no longer available.",
            code="REPORT_EXPIRED",
            status=410
        )
        
    # Mimetypes
    mimetype = "application/pdf"
    if row["format"] == "xlsx":
        mimetype = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        
    filename = f"report_{job_id}.{row['format']}"
    return send_file(
        file_path,
        as_attachment=True,
        download_name=filename,
        mimetype=mimetype
    )

@reports_bp.route("/history", methods=["GET"])
@jwt_required()
def get_reports_history():
    """
    Retrieves history logs of the last 20 reports generated by the authenticated user.
    """
    user_id = get_jwt_identity()
    role = get_jwt().get("role")
    
    history = ReportService.list_reports(user_id, role)
    return success_response(history, "Report generation history retrieved.")

@reports_bp.route("/<job_id>", methods=["DELETE"])
@jwt_required()
def delete_report(job_id):
    """
    Deletes the generated report file from disk and marks the status as 'deleted'.
    """
    user_id = get_jwt_identity()
    role = get_jwt().get("role")
    
    row = qone("SELECT created_by, filters, file_path FROM reports WHERE job_id = %s", (job_id,))
    if not row:
        return error_response("Report job not found", "NOT_FOUND", 404)
        
    if not verify_report_access(row, user_id, role):
        return error_response("Access denied to delete this report", "FORBIDDEN", 403)
        
    # Remove file from disk
    file_path = row["file_path"]
    if file_path and os.path.exists(file_path):
        try:
            os.remove(file_path)
        except Exception as e:
            # Continue marking as deleted in DB even if file delete fails
            pass
            
    # Soft delete in DB
    exe(
        "UPDATE reports SET status = 'deleted', file_path = NULL, file_size = 0 WHERE job_id = %s",
        (job_id,)
    )
    
    return success_response(None, "Report deleted successfully.")
