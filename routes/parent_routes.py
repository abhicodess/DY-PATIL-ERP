from flask import Blueprint, jsonify, request, render_template
from utils.pg_wrapper import qry, qone, exe
from services.parent_notification_service import ParentNotificationService
from services.attendance_service import AttendanceService

parent_bp = Blueprint('parent_comm', __name__, url_prefix='/api/parent')

@parent_bp.route('/dashboard')
def parent_dashboard():
    """Parent Communication Dashboard"""
    return render_template('admin/parent_dashboard.html')

@parent_bp.route('/broadcast', methods=['POST'])
def department_broadcast():
    """Broadcast SMS to parents of a specific department"""
    data = request.json
    dept = data.get('department')
    template = data.get('template_slug')
    context = data.get('context', {})
    
    if not dept or not template:
        return jsonify({"error": "Department and Template required"}), 400
        
    results = ParentNotificationService.broadcast_to_department(dept, template, context)
    return jsonify({
        "status": "success",
        "processed_count": len(results),
        "details": results
    })

@parent_bp.route('/mapping/<int:student_id>', methods=['GET'])
def get_parent_mapping(student_id):
    """Get list of parents mapped to a student"""
    parents = qry("""
        SELECT p.*, m.relationship_type, m.is_primary_contact
        FROM parent_contacts p
        JOIN student_parent_mapping m ON p.id = m.parent_id
        WHERE m.student_id = %s
    """, (student_id,))
    return jsonify([dict(p) for p in parents])

@parent_bp.route('/add-parent', methods=['POST'])
def add_parent_contact():
    """Manually add a parent contact and map to a student"""
    data = request.json
    name = data.get('name')
    phone = data.get('phone')
    student_id = data.get('student_id')
    rel = data.get('relationship', 'Father')
    
    if not name or not phone or not student_id:
        return jsonify({"error": "Name, Phone, and StudentID required"}), 400
        
    # Check if parent exists
    parent = qone("SELECT id FROM parent_contacts WHERE phone_primary=%s", (phone,))
    if not parent:
        p_id = exe("INSERT INTO parent_contacts (full_name, phone_primary) VALUES (%s, %s) RETURNING id", (name, phone))
    else:
        p_id = parent['id']
        
    # Create mapping
    try:
        exe("INSERT INTO student_parent_mapping (student_id, parent_id, relationship_type) VALUES (%s, %s, %s)", (student_id, p_id, rel))
    except Exception:
        pass # already mapped
    
    return jsonify({"success": True, "parent_id": str(p_id)})

@parent_bp.route('/defaulters', methods=['GET'])
def list_defaulters():
    threshold = request.args.get('threshold', 75, type=int)
    dept = request.args.get('department')
    defaulters = AttendanceService.get_defaulters(threshold, dept)
    return jsonify(defaulters)

@parent_bp.route('/notify-defaulters', methods=['POST'])
def notify_defaulters():
    data = request.json
    threshold = data.get('threshold', 75)
    dept = data.get('department')
    
    defaulters = AttendanceService.get_defaulters(threshold, dept)
    results = []
    
    for s in defaulters:
        # Notify parents for each defaulter
        res = ParentNotificationService.notify_student_parents(
            student_id=s['id'],
            category='attendance',
            template_slug='defaulter_alert',
            context={'percentage': str(s['percentage'])}
        )
        results.extend(res)
        
    return jsonify({
        "status": "success",
        "defaulters_notified": len(defaulters),
        "sms_sent": len(results)
    })
