from app import create_app
from tasks.reports.results_reports import generate_student_marksheet

app = create_app()
with app.app_context():
    try:
        # We test student_id=1, which we saw exists in the database
        generate_student_marksheet(
            {"student_id": 1, "semester": ""}, 
            "/app/uploads/reports/test_marksheet.pdf"
        )
        print("Success!")
    except Exception as e:
        import traceback
        traceback.print_exc()
