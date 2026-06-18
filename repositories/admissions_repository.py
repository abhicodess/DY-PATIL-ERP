from utils.pg_wrapper import qry, qone, exe

class AdmissionsRepository:
    def get_all_applications(self, filters=None):
        filters = filters or {}
        query = "SELECT * FROM applications WHERE 1=1"
        params = {}
        if filters.get('department'):
            query += " AND applied_department = :department"
            params['department'] = filters['department']
        if filters.get('category'):
            query += " AND category = :category"
            params['category'] = filters['category']
        if filters.get('status'):
            query += " AND status = :status"
            params['status'] = filters['status']
        if filters.get('date_start'):
            query += " AND submitted_at >= :date_start"
            params['date_start'] = filters['date_start']
        if filters.get('date_end'):
            query += " AND submitted_at <= :date_end"
            params['date_end'] = filters['date_end']
        query += " ORDER BY submitted_at DESC"
        return qry(query, params)

    def get_application_by_id(self, application_id):
        return qone("SELECT * FROM applications WHERE id = :id", {"id": application_id})

    def get_application_by_token(self, token):
        return qone("SELECT * FROM applications WHERE token = :token", {"token": token})

    def create_application(self, data):
        sql = """
            INSERT INTO applications (
                token, applicant_name, applicant_email, applicant_phone, 
                date_of_birth, gender, category, domicile_state, 
                applied_department, applied_year, status, merit_score
            ) VALUES (
                :token, :applicant_name, :applicant_email, :applicant_phone, 
                :date_of_birth, :gender, :category, :domicile_state, 
                :applied_department, :applied_year, :status, :merit_score
            ) RETURNING id
        """
        res = qone(sql, {
            'token': data.get('token'),
            'applicant_name': data.get('applicant_name'),
            'applicant_email': data.get('applicant_email'),
            'applicant_phone': data.get('applicant_phone'),
            'date_of_birth': data.get('date_of_birth'),
            'gender': data.get('gender'),
            'category': data.get('category'),
            'domicile_state': data.get('domicile_state'),
            'applied_department': data.get('applied_department'),
            'applied_year': data.get('applied_year'),
            'status': data.get('status', 'PENDING'),
            'merit_score': data.get('merit_score')
        })
        return res['id'] if res else None

    def update_application_status(self, application_id, status, remarks, updated_by):
        sql = """
            UPDATE applications 
            SET status = :status, remarks = :remarks, reviewed_by = :reviewed_by, reviewed_at = NOW(), updated_at = NOW() 
            WHERE id = :id
        """
        exe(sql, {
            "status": status,
            "remarks": remarks,
            "reviewed_by": updated_by,
            "id": application_id
        })

    def update_application_rank(self, application_id, rank, status=None):
        if status:
            sql = "UPDATE applications SET rank_in_department = :rank, status = :status, updated_at = NOW() WHERE id = :id"
            exe(sql, {"rank": rank, "status": status, "id": application_id})
        else:
            sql = "UPDATE applications SET rank_in_department = :rank, updated_at = NOW() WHERE id = :id"
            exe(sql, {"rank": rank, "id": application_id})

    def get_documents_by_application(self, application_id):
        return qry("SELECT * FROM application_documents WHERE application_id = :application_id", {"application_id": application_id})

    def create_document(self, data):
        sql = """
            INSERT INTO application_documents (
                application_id, document_type, file_name, file_path, file_size
            ) VALUES (
                :application_id, :document_type, :file_name, :file_path, :file_size
            ) RETURNING id
        """
        res = qone(sql, {
            'application_id': data.get('application_id'),
            'document_type': data.get('document_type'),
            'file_name': data.get('file_name'),
            'file_path': data.get('file_path'),
            'file_size': data.get('file_size')
        })
        return res['id'] if res else None

    def verify_document(self, document_id, admin_id):
        sql = """
            UPDATE application_documents 
            SET verified = TRUE, verified_by = :admin_id, verified_at = NOW() 
            WHERE id = :id
        """
        exe(sql, {"admin_id": admin_id, "id": document_id})

    def get_merit_list(self, department, category, year):
        sql = """
            SELECT * FROM merit_lists 
            WHERE department = :department AND category = :category AND academic_year = :academic_year 
            ORDER BY rank ASC
        """
        return qry(sql, {"department": department, "category": category, "academic_year": year})

    def clear_provisional_merit_list(self, department, category, year):
        sql = """
            DELETE FROM merit_lists 
            WHERE department = :department AND category = :category AND academic_year = :academic_year AND status = 'PROVISIONAL'
        """
        exe(sql, {"department": department, "category": category, "academic_year": year})

    def insert_merit_list_entry(self, data):
        sql = """
            INSERT INTO merit_lists (
                department, category, academic_year, application_id, merit_score, rank, status, generated_by
            ) VALUES (
                :department, :category, :academic_year, :application_id, :merit_score, :rank, :status, :generated_by
            )
        """
        exe(sql, data)

    def finalize_merit_list_entries(self, department, category, year):
        sql = """
            UPDATE merit_lists 
            SET status = 'FINAL' 
            WHERE department = :department AND category = :category AND academic_year = :academic_year AND status = 'PROVISIONAL'
        """
        exe(sql, {"department": department, "category": category, "academic_year": year})

    def get_seat_matrix(self, year):
        return qry("SELECT * FROM seat_matrix WHERE academic_year = :academic_year", {"academic_year": year})

    def get_seat_matrix_entry(self, department, category, year):
        sql = """
            SELECT * FROM seat_matrix 
            WHERE department = :department AND category = :category AND academic_year = :academic_year
        """
        return qone(sql, {"department": department, "category": category, "academic_year": year})

    def update_seat_matrix_filled(self, department, category, year, filled_increment):
        sql = """
            UPDATE seat_matrix 
            SET filled_seats = filled_seats + :increment, 
                available_seats = total_seats - (filled_seats + :increment),
                last_updated = NOW() 
            WHERE department = :department AND category = :category AND academic_year = :academic_year
        """
        exe(sql, {"increment": filled_increment, "department": department, "category": category, "academic_year": year})

    def log_timeline(self, application_id, action, by, notes):
        sql = """
            INSERT INTO application_timeline (
                application_id, action, action_by, notes
            ) VALUES (
                :application_id, :action, :action_by, :notes
            )
        """
        exe(sql, {"application_id": application_id, "action": action, "action_by": by, "notes": notes})
