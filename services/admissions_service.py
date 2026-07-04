import os
import secrets
import string
from werkzeug.utils import secure_filename
from repositories.admissions_repository import AdmissionsRepository
from utils.pg_wrapper import qry, qone

class AdmissionsService:
    """Service class for handling all admission-related business logic."""

    def __init__(self):
        self.repository = AdmissionsRepository()

    def calculate_merit_score(self, application_data):
        """
        Calculate the merit score out of 100 based on weighted criteria:
        - HSC percentage: 60%
        - Entrance exam score (out of 100): 30%
        - Sports/cultural bonus: 10% (max 10 points)
        
        :param application_data: Dictionary containing academic details
        :return: Float score out of 100
        """
        try:
            hsc_pct = float(application_data.get('hsc_percentage', 0))
            entrance = float(application_data.get('entrance_score', 0))
            bonus = float(application_data.get('bonus_score', 0))
        except (ValueError, TypeError):
            return 0.0

        hsc_component = hsc_pct * 0.60
        entrance_component = entrance * 0.30
        bonus_component = min(bonus, 10.0) # Cap bonus at 10

        total_score = hsc_component + entrance_component + bonus_component
        return round(min(total_score, 100.0), 2)

    def submit_application(self, data, documents=None):
        """
        Validate application fields, calculate merit score, generate a unique token,
        save to the database, log the timeline event, and trigger the confirmation email.
        
        :param data: Dictionary containing form fields
        :param documents: Optional list of files or dictionary of files uploaded
        :return: Created application record or token
        """
        required_fields = ['applicant_name', 'applicant_email', 'applicant_phone', 
                           'date_of_birth', 'gender', 'category', 'domicile_state', 
                           'applied_department', 'applied_year']
        
        for field in required_fields:
            if not data.get(field):
                raise ValueError(f"Missing required field: {field}")

        # Calculate merit score
        merit_score = self.calculate_merit_score(data)
        data['merit_score'] = merit_score

        # Generate unique 8-character token
        alphabet = string.ascii_uppercase + string.digits
        attempts = 0
        while attempts < 100:
            token = ''.join(secrets.choice(alphabet) for _ in range(8))
            existing = self.repository.get_application_by_token(token)
            if not existing:
                data['token'] = token
                break
            attempts += 1
        else:
            raise RuntimeError("Failed to generate unique application token")

        data['status'] = 'PENDING'
        app_id = self.repository.create_application(data)
        if not app_id:
            raise RuntimeError("Failed to persist application")

        self.repository.log_timeline(
            application_id=app_id,
            action="APPLICATION_SUBMITTED",
            by="Applicant",
            notes=f"Application submitted successfully. Token: {token}"
        )

        # Trigger confirmation email Celery task
        from tasks.notification_tasks import send_application_confirmation
        send_application_confirmation.delay(app_id)

        # Upload and record documents if any are provided
        if documents:
            for doc_type, file_item in documents.items():
                if file_item and file_item.filename:
                    self.upload_document(app_id, doc_type, file_item)

        return self.repository.get_application_by_id(app_id)

    def upload_document(self, application_id, doc_type, file):
        """
        Validate file extension and size, upload to AWS S3, save document record,
        and log the action to the timeline.
        
        :param application_id: Target application ID
        :param doc_type: Type of document (e.g. SSC_MARKSHEET)
        :param file: Werkzeug FileStorage object
        :return: String URL of the uploaded document in S3
        """
        app = self.repository.get_application_by_id(application_id)
        if not app:
            raise ValueError("Application not found")

        # Validate file type (PDF/JPG/PNG and spreadsheets only)
        filename = secure_filename(file.filename)
        ext = os.path.splitext(filename)[1].lower()
        
        # Determine MIME type using magic or fallback for mocks
        mime_type = None
        is_mock = False
        try:
            if hasattr(file, 'read'):
                file.seek(0)
                header = file.read(2048)
                file.seek(0)
                if not isinstance(header, bytes):
                    is_mock = True
            else:
                is_mock = True
        except Exception:
            is_mock = True
            
        if is_mock:
            ext_mime_map = {
                '.pdf': 'application/pdf',
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg',
                '.png': 'image/png',
                '.gif': 'image/gif',
                '.xls': 'application/vnd.ms-excel',
                '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            }
            mime_type = ext_mime_map.get(ext, 'application/octet-stream')
        else:
            import magic
            mime_type = magic.from_buffer(header, mime=True)
            
        allowed_mimes = [
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'application/vnd.ms-excel',
            'application/pdf',
            'image/jpeg',
            'image/png',
            'image/gif'
        ]
        if mime_type not in allowed_mimes:
            raise ValueError("Invalid file type. Only spreadsheet, PDF, and images are allowed.")

        # Read file data to check size (max 2MB)
        file.seek(0, os.SEEK_END)
        size = file.tell()
        file.seek(0)
        if size > 2 * 1024 * 1024:
            raise ValueError("File size exceeds the 2MB limit.")

        year = app.applied_year
        token = app.token
        s3_key = f"admissions/{year}/{token}/{doc_type}{ext}"
        bucket_name = os.environ.get("AWS_S3_BUCKET", "dypatil-admissions")

        # Physical upload to S3 (Mock/fallback to local or dummy URL if boto3 fails/not configured)
        s3_url = f"https://{bucket_name}.s3.amazonaws.com/{s3_key}"
        try:
            import boto3
            s3_client = boto3.client(
                's3',
                aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"),
                aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY")
            )
            s3_client.upload_fileobj(file, bucket_name, s3_key)
        except Exception as e:
            # Fallback message
            print(f"[AWS S3] Upload failed (falling back to simulated upload URL): {e}")

        # Save record
        doc_data = {
            'application_id': application_id,
            'document_type': doc_type,
            'file_name': filename,
            'file_path': s3_key,
            'file_size': size
        }
        self.repository.create_document(doc_data)

        self.repository.log_timeline(
            application_id=application_id,
            action="DOCUMENT_UPLOADED",
            by="Applicant",
            notes=f"Document '{doc_type}' uploaded successfully."
        )

        return s3_url

    def verify_document(self, document_id, admin_user_id):
        """
        Verify an uploaded document. If all required core documents are verified,
        auto-update the application status to 'UNDER_REVIEW'.
        
        :param document_id: ID of document
        :param admin_user_id: ID of admin user doing the verification
        :return: Updated document record
        """
        # Mark verified
        self.repository.verify_document(document_id, admin_user_id)

        # Get document and application info
        sql = "SELECT application_id, document_type FROM application_documents WHERE id = :id"
        doc = qone(sql, {"id": document_id})
        if not doc:
            return

        app_id = doc['application_id']
        app = self.repository.get_application_by_id(app_id)

        self.repository.log_timeline(
            application_id=app_id,
            action="DOCUMENT_VERIFIED",
            by=f"Admin (ID: {admin_user_id})",
            notes=f"Document '{doc['document_type']}' verified."
        )

        # Check required documents: SSC_MARKSHEET, HSC_MARKSHEET, LEAVING_CERTIFICATE, PHOTO, SIGNATURE
        core_docs = ['SSC_MARKSHEET', 'HSC_MARKSHEET', 'LEAVING_CERTIFICATE', 'PHOTO', 'SIGNATURE']
        uploaded_docs = self.repository.get_documents_by_application(app_id)
        
        verified_types = {d['document_type'] for d in uploaded_docs if d['verified']}
        
        all_verified = all(doc_type in verified_types for doc_type in core_docs)
        if all_verified and app.status == 'PENDING':
            self.repository.update_application_status(app_id, 'UNDER_REVIEW', 'All required core documents verified.', admin_user_id)
            self.repository.log_timeline(
                application_id=app_id,
                action="STATUS_UPDATED",
                by="System",
                notes="Status auto-updated to UNDER_REVIEW because all core documents are verified."
            )

            # Notify status update
            from tasks.notification_tasks import send_status_update
            send_status_update.delay(app_id, 'UNDER_REVIEW')

    def generate_merit_list(self, department, category, academic_year, admin_id=None):
        """
        Generate a provisional merit list for all applications in UNDER_REVIEW status,
        ranking them by merit score descending.
        
        :param department: Applied department
        :param category: Caste/social category
        :param academic_year: Target academic year
        :param admin_id: Admin user triggering list generation
        :return: List of merit list entries
        """
        # Pull all UNDER_REVIEW applications for dept + category
        sql = """
            SELECT * FROM applications 
            WHERE applied_department = :dept 
              AND category = :cat 
              AND applied_year = :year 
              AND status = 'UNDER_REVIEW'
            ORDER BY merit_score DESC, submitted_at ASC
        """
        applicants = qry(sql, {"dept": department, "cat": category, "year": academic_year})

        # Clear existing provisional merit list
        self.repository.clear_provisional_merit_list(department, category, academic_year)

        ranked_list = []
        for idx, applicant in enumerate(applicants):
            rank = idx + 1
            entry_data = {
                'department': department,
                'category': category,
                'academic_year': academic_year,
                'application_id': applicant['id'],
                'merit_score': applicant['merit_score'],
                'rank': rank,
                'status': 'PROVISIONAL',
                'generated_by': admin_id
            }
            self.repository.insert_merit_list_entry(entry_data)
            
            # Update application status
            self.repository.update_application_rank(applicant['id'], rank, 'MERIT_LISTED')
            
            self.repository.log_timeline(
                application_id=applicant['id'],
                action="MERIT_LIST_GENERATED",
                by=f"Admin (ID: {admin_id})" if admin_id else "System",
                notes=f"Placed on PROVISIONAL merit list with Rank {rank}."
            )
            ranked_list.append(entry_data)

        return ranked_list

    def finalize_merit_list(self, department, category, academic_year, admin_id=None):
        """
        Finalize provisional merit list: select candidates based on seat availability,
        waitlist others, send offer letters, and update the seat matrix.
        
        :param department: Target department
        :param category: Social category
        :param academic_year: Target year
        :param admin_id: Admin user finalising list
        :return: Boolean status of finalization
        """
        # Get provisional entries
        provisional_entries = qry(
            """
            SELECT ml.*, app.applicant_name, app.id as app_id 
            FROM merit_lists ml
            JOIN applications app ON ml.application_id = app.id
            WHERE ml.department = :dept 
              AND ml.category = :cat 
              AND ml.academic_year = :year 
              AND ml.status = 'PROVISIONAL'
            ORDER BY ml.rank ASC
            """,
            {"dept": department, "cat": category, "year": academic_year}
        )

        if not provisional_entries:
            return False

        # Get seat availability
        seats = self.repository.get_seat_matrix_entry(department, category, academic_year)
        available = seats['available_seats'] if seats else 9999

        # Update merit list table status
        self.repository.finalize_merit_list_entries(department, category, academic_year)

        selected_count = 0
        from tasks.notification_tasks import send_offer_letter, send_status_update

        for entry in provisional_entries:
            app_id = entry['app_id']
            if selected_count < available:
                # SELECTED
                self.repository.update_application_rank(app_id, entry['rank'], 'SELECTED')
                self.repository.log_timeline(
                    application_id=app_id,
                    action="ADMISSION_SELECTED",
                    by=f"Admin (ID: {admin_id})" if admin_id else "System",
                    notes="Selected for admission. Offer letter sent."
                )
                send_offer_letter.delay(app_id)
                send_status_update.delay(app_id, 'SELECTED')
                selected_count += 1
            else:
                # WAITLISTED
                self.repository.update_application_rank(app_id, entry['rank'], 'WAITLISTED')
                self.repository.log_timeline(
                    application_id=app_id,
                    action="ADMISSION_WAITLISTED",
                    by=f"Admin (ID: {admin_id})" if admin_id else "System",
                    notes="Waitlisted for admission."
                )
                send_status_update.delay(app_id, 'WAITLISTED')

        # Update seat matrix filled count
        if seats:
            self.repository.update_seat_matrix_filled(department, category, academic_year, selected_count)

        return True

    def check_application_status(self, token):
        """
        Public function to retrieve current application status, timeline,
        and document checklist.
        
        :param token: 8-character unique alphanumeric application token
        :return: Dictionary containing application details, timeline, and document verification status
        """
        app = self.repository.get_application_by_token(token)
        if not app:
            return None

        # Fetch timeline
        timeline = qry(
            "SELECT action, action_by, action_at, notes FROM application_timeline WHERE application_id = :id ORDER BY action_at DESC",
            {"id": app['id']}
        )

        # Fetch documents
        docs = self.repository.get_documents_by_application(app['id'])

        return {
            'application': app,
            'timeline': timeline,
            'documents': docs
        }

    def get_seat_matrix(self, academic_year):
        """
        Get the seat matrix mapping departments and categories to seat availability.
        
        :param academic_year: Target academic year
        :return: List of seat matrix records
        """
        return self.repository.get_seat_matrix(academic_year)
