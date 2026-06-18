from flask import Blueprint, jsonify, request
from services.otp_service import OTPService
from extensions import limiter

otp_bp = Blueprint('otp', __name__, url_prefix='/api/auth')

@otp_bp.route('/request-otp', methods=['POST'])
@limiter.limit("5 per minute")
def request_otp():
    data = request.json
    phone = data.get('phone')
    
    if not phone:
        return jsonify({"success": False, "error": "Phone number required"}), 400
        
    res = OTPService.generate_and_send_otp(phone)
    return jsonify(res)

@otp_bp.route('/verify-otp', methods=['POST'])
@limiter.limit("5 per minute")
def verify_otp():
    data = request.json
    phone = data.get('phone')
    code = data.get('code')
    
    if not phone or not code:
        return jsonify({"success": False, "error": "Phone and Code required"}), 400
        
    res = OTPService.verify_otp(phone, code)
    
    # In a real production app, you would create a session/JWT token here
    if res['success']:
        # TODO: Create user session
        pass
        
    return jsonify(res)
