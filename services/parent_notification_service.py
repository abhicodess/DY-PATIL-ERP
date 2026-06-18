from services.sms_service import SMSService
from utils.pg_wrapper import qry, qone

class ParentNotificationService:
    """
    High-level service to manage student-parent communication.
    Handles preference filtering and dynamic placeholders.
    """
    
    @staticmethod
    def notify_student_parents(student_id: int, category: str, template_slug: str, context: dict) -> list:
        """
        Sends an SMS to all primary parents of a student.
        Category examples: 'attendance', 'fees', 'exams'.
        """
        # 1. Fetch Student Name (for breadcrumbs)
        std = qone("SELECT name FROM students WHERE id=%s", (student_id,))
        if not std:
            return [{"success": False, "error": "Student not found"}]
            
        context['student_name'] = std['name']

        # 2. Get all Primary Parents associated with this student
        parents = qry("""
            SELECT p.id, p.full_name, p.phone_primary 
            FROM parent_contacts p
            JOIN student_parent_mapping m ON p.id = m.parent_id
            WHERE m.student_id = %s AND m.is_primary_contact = True
        """, (student_id,))

        results = []
        for parent in parents:
            # 3. Check Notification Preference
            pref = qone("""
                SELECT is_enabled FROM notification_preferences 
                WHERE parent_id = %s AND category = %s
            """, (parent['id'], category))

            # Enable by default if no setting found
            if pref and not pref['is_enabled']:
                print(f"Skipping {parent['phone_primary']} due to parent preferences.")
                continue

            # 4. Personalize contexts
            p_context = context.copy()
            p_context['parent_name'] = parent['full_name']
            
            # 5. Queue SMS via the SMSService
            res = SMSService.queue_sms(parent['phone_primary'], template_slug, p_context)
            results.append({"parent": parent['full_name'], **res})
            
        return results

    @staticmethod
    def broadcast_to_department(department: str, template_slug: str, context: dict):
        """
        Broadcasts an announcement to all parents of students in a specific department.
        Example: 'Holiday announcement'
        """
        students = qry("SELECT id FROM students WHERE department=%s", (department,))
        all_results = []
        for s in students:
            res = ParentNotificationService.notify_student_parents(s['id'], 'general', template_slug, context)
            all_results.extend(res)
        return all_results
