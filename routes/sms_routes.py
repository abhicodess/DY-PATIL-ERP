from flask import Blueprint, jsonify, request
from utils.pg_wrapper import qry, qone, exe
from services.sms_service import SMSService
import json

sms_bp = Blueprint('sms', __name__, url_prefix='/api/sms')

@sms_bp.route('/history', methods=['GET'])
def get_sms_history():
    """Fetch recent SMS logs"""
    limit = request.args.get('limit', 50, type=int)
    logs = qry("SELECT * FROM sms_logs ORDER BY created_at DESC LIMIT %s", (limit,))
    
    # Process UUID and JSONB for frontend
    out = []
    for log in logs:
        d = dict(log)
        d['id'] = str(d['id'])
        d['created_at'] = d['created_at'].isoformat() if d['created_at'] else None
        d['updated_at'] = d['updated_at'].isoformat() if d['updated_at'] else None
        out.append(d)
        
    return jsonify(out)

@sms_bp.route('/templates', methods=['GET'])
def get_templates():
    """Fetch all SMS templates"""
    templates = qry("SELECT * FROM sms_templates WHERE is_active=True ORDER BY slug")
    out = [dict(t) for t in templates]
    for t in out:
        t['created_at'] = t['created_at'].isoformat() if t['created_at'] else None
    return jsonify(out)

@sms_bp.route('/analytics', methods=['GET'])
def get_analytics():
    """Summary stats for the dashboard"""
    stats = qone("""
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN status='delivered' THEN 1 ELSE 0 END) as delivered,
            SUM(CASE WHEN status='failed' THEN 1 ELSE 0 END) as failed,
            SUM(CASE WHEN status='queued' THEN 1 ELSE 0 END) as queued
        FROM sms_logs
    """)
    return jsonify(dict(stats))

@sms_bp.route('/send-test', methods=['POST'])
def send_test_sms():
    """Trigger a manual test SMS from the dashboard"""
    data = request.json
    recipient = data.get('recipient')
    slug = data.get('slug', 'welcome_msg')
    context = data.get('context', {"name": "User"})
    
    if not recipient:
        return jsonify({"error": "Recipient required"}), 400
        
    result = SMSService.send_immediate(recipient, slug, context)
    return jsonify(result)
