from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from utils.pg_wrapper import qry, qone, exe
from utils.api_response import success_response, error_response, paginated_response
from api.v1.auth import jwt_role_required
import datetime

notifications_bp = Blueprint('notifications', __name__)

@notifications_bp.route("", methods=["GET"])
@jwt_required()
def get_notifications():
    """
    Get notifications for the logged in student or faculty.
    """
    identity_id = int(get_jwt_identity())
    claims = get_jwt()
    role = claims.get("role")

    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 20))
    offset = (page - 1) * per_page

    query = """
        SELECT m.id, m.sender_id, m.sender_role, m.receiver_id, m.receiver_role, m.subject, m.body, m.created_at::TEXT,
               (nr.id IS NOT NULL) as is_read
        FROM messages m
        LEFT JOIN notification_reads nr ON m.id = nr.notification_id AND nr.user_id = :user_id AND nr.role = :role
        WHERE 1=1
    """
    params = {"user_id": identity_id, "role": role}

    if role == "student":
        query += " AND m.receiver_role = 'student' AND (m.receiver_id = :user_id OR m.receiver_id = 0)"
    elif role == "faculty":
        query += " AND m.receiver_role = 'faculty' AND (m.receiver_id = :user_id OR m.receiver_id = 0)"
    elif role == "admin":
        # Admin can view all messages they created
        query += " AND m.sender_role = 'admin'"
    else:
        return error_response("Invalid role access", "FORBIDDEN", 403)

    count_query = f"SELECT COUNT(*) as cnt FROM ({query}) as src"
    total = qone(count_query, params)['cnt']

    query += " ORDER BY m.created_at DESC LIMIT :limit OFFSET :offset"
    params['limit'] = per_page
    params['offset'] = offset

    records = qry(query, params)
    return paginated_response([dict(r) for r in records], total, page, per_page)

@notifications_bp.route("/<int:msg_id>/read", methods=["POST"])
@jwt_required()
def mark_notification_read(msg_id):
    """
    Mark a notification as read.
    """
    identity_id = int(get_jwt_identity())
    claims = get_jwt()
    role = claims.get("role")

    # Check if notification exists
    msg = qone("SELECT id FROM messages WHERE id = :id", {"id": msg_id})
    if not msg:
        return error_response("Notification not found", "NOT_FOUND", 404)

    # Insert read record
    try:
        exe("""
            INSERT INTO notification_reads (user_id, role, notification_id)
            VALUES (%s, %s, %s)
            ON CONFLICT (user_id, role, notification_id) DO NOTHING
        """, (identity_id, role, msg_id))
    except Exception as e:
        return error_response(str(e), "READ_MARK_FAILED", 500)

    return success_response(None, "Notification marked as read")

@notifications_bp.route("", methods=["POST"])
@jwt_role_required(["admin"])
def create_notification():
    """
    Send/Broadcast a new notification.
    """
    body = request.get_json() or {}
    receiver_role = body.get("receiver_role", "student") # student, faculty, all
    receiver_id = body.get("receiver_id", 0) # 0 means broadcast to all
    subject = body.get("subject", "").strip()
    content = body.get("body", "").strip()

    if not subject or not content:
        return error_response("Missing required parameters: subject or body", "VALIDATION_ERROR", 422)

    identity_id = int(get_jwt_identity())

    exe("""
        INSERT INTO messages (sender_id, sender_role, receiver_id, receiver_role, subject, body, is_read)
        VALUES (%s, %s, %s, %s, %s, %s, false)
    """, (identity_id, "admin", receiver_id, receiver_role, subject, content))

    return success_response(None, "Notification broadcasted successfully")
