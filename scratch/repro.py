import os
import sys

os.environ['SECRET_KEY'] = 'placeholder_secret_key_for_testing_purposes_only_32_chars'
os.environ['JWT_SECRET_KEY'] = 'placeholder_jwt_secret_key_for_testing_purposes_only_32_chars'
os.environ['DEFAULT_STUDENT_PASSWORD'] = 'D0pdb2Bg5riRvtAa'
os.environ['DEFAULT_FACULTY_PASSWORD'] = 'fT-_Ok4-YxUMtuKF'

sys.path.insert(0, os.path.abspath('.'))

import app
from tests.test_attendance_upload import build_report_file
from routes.upload_attendance import process_attendance_upload

# Create app context
flask_app = app.create_app()
with flask_app.app_context():
    file_obj = build_report_file()
    session_obj = {"role": "admin", "name": "Administrator"}
    
    # We will call the function directly without catching exceptions to see where it fails
    from models.attendance import persist_attendance_upload
    from services.excel_parser import parse_attendance_excel
    
    parse_result = parse_attendance_excel(file_obj)
    parse_result.metadata["source_filename"] = getattr(file_obj, "filename", "") or ""
    
    # Run the persist function directly to trigger the exception
    persist_attendance_upload(parse_result, "admin", 1)
