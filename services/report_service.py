import os
import uuid
import json
from datetime import datetime, timedelta
from celery_app import celery
from utils.pg_wrapper import qry, qone, exe

class ReportValidationError(ValueError):
    pass

REPORT_REGISTRY = {
    "monthly_attendance": {
        "task": "tasks.reports.attendance_reports.generate_monthly_attendance_report",
        "name": "Monthly Attendance Summary",
        "description": "Monthly attendance summary with class averages, percentage indicators, and visualization.",
        "allowed_roles": ["admin", "faculty"],
        "required_filters": ["department", "month", "academic_year"],
        "optional_filters": ["year", "division"],
        "formats": ["pdf", "xlsx"],
        "estimated_seconds": 30
    },
    "defaulter_report": {
        "task": "tasks.reports.attendance_reports.generate_defaulter_report",
        "name": "Attendance Defaulter List",
        "description": "Urgent alert list of students falling below a threshold, grouped by department.",
        "allowed_roles": ["admin", "faculty"],
        "required_filters": ["department", "as_of_date"],
        "optional_filters": ["year", "threshold"],
        "formats": ["pdf", "xlsx"],
        "estimated_seconds": 20
    },
    "student_marksheet": {
        "task": "tasks.reports.results_reports.generate_student_marksheet",
        "name": "Semester Marksheet",
        "description": "Student marksheet containing grades, SGPA, and a verification QR code.",
        "allowed_roles": ["admin", "student"],
        "required_filters": ["student_id", "semester"],
        "optional_filters": [],
        "formats": ["pdf"],
        "estimated_seconds": 10
    },
    "class_result_analysis": {
        "task": "tasks.reports.results_reports.generate_class_result_analysis",
        "name": "Class Result Analysis",
        "description": "Complex class performance breakdown with donut charts and subject-wise averages.",
        "allowed_roles": ["admin", "faculty"],
        "required_filters": ["department", "year", "semester"],
        "optional_filters": ["division"],
        "formats": ["pdf"],
        "estimated_seconds": 45
    },
    "faculty_attendance": {
        "task": "tasks.reports.hr_reports.generate_faculty_attendance_report",
        "name": "Faculty Attendance Summary",
        "description": "Working days and attendance percentages for department faculty members.",
        "allowed_roles": ["admin"],
        "required_filters": ["month", "academic_year"],
        "optional_filters": ["department"],
        "formats": ["pdf", "xlsx"],
        "estimated_seconds": 15
    },
    "faculty_workload": {
        "task": "tasks.reports.hr_reports.generate_faculty_workload_report",
        "name": "Faculty Workload Analysis",
        "description": "Timetable loads, lectures scheduled versus lectures taken.",
        "allowed_roles": ["admin"],
        "required_filters": ["semester", "academic_year"],
        "optional_filters": ["department"],
        "formats": ["pdf", "xlsx"],
        "estimated_seconds": 20
    },
    "institution_summary": {
        "task": "tasks.reports.hr_reports.generate_institution_summary",
        "name": "Institution Executive Summary",
        "description": "High-level summary of enrollments, attendance, and results across all departments.",
        "allowed_roles": ["admin"],
        "required_filters": ["academic_year", "as_of_date"],
        "optional_filters": [],
        "formats": ["pdf"],
        "estimated_seconds": 60
    },
    "timetable_export": {
        "task": "tasks.reports.attendance_reports.generate_timetable_pdf",
        "name": "Class Timetable Grid",
        "description": "Weekly timetable grid formatted for a specific division and semester.",
        "allowed_roles": ["admin", "faculty", "student"],
        "required_filters": ["department", "year", "division", "semester"],
        "optional_filters": [],
        "formats": ["pdf"],
        "estimated_seconds": 15
    }
}

def validate_filters(report_type, filters, user):
    """
    Validates report request filters against the registry.
    Raises ReportValidationError if invalid.
    """
    if report_type not in REPORT_REGISTRY:
        raise ReportValidationError(f"Invalid report type: {report_type}")
        
    config = REPORT_REGISTRY[report_type]
    
    # Role validation
    user_role = user.get("role")
    if user_role not in config["allowed_roles"]:
        raise ReportValidationError(f"User role '{user_role}' is not authorized to generate '{report_type}' reports.")
        
    # Required filters validation
    for f in config["required_filters"]:
        if f not in filters or filters[f] is None or filters[f] == "":
            raise ReportValidationError(f"Missing required filter: '{f}'")
            
    # Role-based scoping/security validation
    if user_role == "faculty":
        # Faculty can only generate for their own department (if department is specified/required)
        user_dept = user.get("department")
        if "department" in filters and user_dept and filters["department"] != user_dept:
            raise ReportValidationError(f"Access denied: Faculty belongs to department '{user_dept}' and cannot generate reports for '{filters['department']}'.")
            
    elif user_role == "student":
        # Students can only generate their own marksheet
        if report_type == "student_marksheet":
            student_id = int(filters.get("student_id"))
            user_id = int(user.get("id"))
            if student_id != user_id:
                raise ReportValidationError("Access denied: Students can only generate their own marksheet.")
        # Students can only view their own department's timetable
        elif report_type == "timetable_export":
            user_dept = user.get("department")
            if "department" in filters and user_dept and filters["department"] != user_dept:
                raise ReportValidationError(f"Access denied: Students cannot access timetables outside department '{user_dept}'.")

class ReportService:
    @staticmethod
    def generate(report_type, format, filters, requested_by):
        """
        Validates filters, registers report in DB, and queues the celery task.
        Returns job_id.
        """
        if format not in ["pdf", "xlsx"]:
            raise ReportValidationError("Invalid format. Must be 'pdf' or 'xlsx'.")
            
        if report_type not in REPORT_REGISTRY:
            raise ReportValidationError(f"Invalid report type: {report_type}")
            
        if format not in REPORT_REGISTRY[report_type]["formats"]:
            raise ReportValidationError(f"Format '{format}' is not supported for report type '{report_type}'.")

        # Validate filters
        validate_filters(report_type, filters, requested_by)
        
        job_id = uuid.uuid4()
        user_id = requested_by.get("id")
        user_role = requested_by.get("role")
        
        # Enforce created_by referencing students(id) for FK constraint integrity
        db_created_by = user_id if user_role == "student" else None
        
        # Add metadata into filters for persistence and history tracking
        filters_with_meta = dict(filters)
        filters_with_meta["_meta"] = {
            "user_id": user_id,
            "role": user_role,
            "name": requested_by.get("name"),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Store report metadata in PostgreSQL
        exe(
            """
            INSERT INTO reports (job_id, report_type, format, filters, status, progress, created_by)
            VALUES (%s, %s, %s, %s, 'queued', 0, %s)
            """,
            (str(job_id), report_type, format, json.dumps(filters_with_meta), db_created_by)
        )
        
        # Setup output path
        output_dir = os.environ.get("REPORT_OUTPUT_DIR", "/app/uploads/reports")
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, f"{job_id}.{format}")
        
        # Determine queue based on report type
        queue_name = "default"
        if report_type == "institution_summary":
            queue_name = "bulk"
            
        # Dispatch to celery task
        from utils.tenant_context import get_tenant_id
        task_name = REPORT_REGISTRY[report_type]["task"]
        celery.send_task(
            task_name,
            args=[filters_with_meta, output_path],
            kwargs={"_tenant_id": get_tenant_id()},
            task_id=str(job_id),
            queue=queue_name
        )
        
        return str(job_id)

    @staticmethod
    def get_status(job_id):
        """
        Retrieves report generation status.
        """
        row = qone(
            "SELECT status, progress, error_msg, file_path, format FROM reports WHERE job_id = %s",
            (job_id,)
        )
        if not row:
            return None
            
        download_url = None
        if row["status"] == "done" and row["file_path"]:
            download_url = f"/api/v1/reports/download/{job_id}"
            
        return {
            "status": row["status"],
            "progress": row["progress"],
            "download_url": download_url,
            "error": row["error_msg"]
        }

    @staticmethod
    def list_reports(user_id, role):
        """
        Lists reports. If student, only list their reports.
        If faculty or admin, list reports they created (via JSONB filter).
        """
        if role == "student":
            rows = qry(
                """
                SELECT job_id, report_type, format, created_at, status, file_size, filters
                FROM reports
                WHERE created_by = %s
                ORDER BY created_at DESC
                LIMIT 20
                """,
                (user_id,)
            )
        else:
            # Check the JSONB _meta user_id and role
            rows = qry(
                """
                SELECT job_id, report_type, format, created_at, status, file_size, filters
                FROM reports
                WHERE filters->'_meta'->>'user_id' = %s AND filters->'_meta'->>'role' = %s
                ORDER BY created_at DESC
                LIMIT 20
                """,
                (str(user_id), role)
            )
            
        results = []
        for r in rows:
            job_id_str = str(r["job_id"])
            download_url = f"/api/v1/reports/download/{job_id_str}" if r["status"] == "done" else None
            
            # Look up clean display name
            registry_info = REPORT_REGISTRY.get(r["report_type"], {})
            name = registry_info.get("name", r["report_type"].replace("_", " ").title())
            
            # Clean filters for frontend regeneration
            try:
                raw_filters = json.loads(r["filters"]) if isinstance(r["filters"], str) else r["filters"]
                clean_filters = {k: v for k, v in raw_filters.items() if k != "_meta"}
            except Exception:
                clean_filters = {}
            
            results.append({
                "job_id": job_id_str,
                "report_type": r["report_type"],
                "name": name,
                "format": r["format"],
                "created_at": r["created_at"].isoformat() if isinstance(r["created_at"], datetime) else r["created_at"],
                "status": r["status"],
                "file_size": r["file_size"],
                "url": download_url,
                "filters": clean_filters
            })
        return results
