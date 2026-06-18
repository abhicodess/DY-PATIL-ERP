import os
import pandas as pd
from flask import Flask, render_template, request, redirect, url_for, flash
from models import db, Student, Subject, Result
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['SECRET_KEY'] = 'supersecretkey'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///results.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db.init_app(app)

@app.route('/')
def index():
    divisions = ['A', 'B', 'C', 'D']
    selected_div = request.args.get('division', '')
    selected_sem = request.args.get('semester', '')
    
    query = Student.query
    if selected_div in divisions:
        query = query.filter(Student.division == selected_div)
    
    # We can filter students who have results in that semester
    if selected_sem:
        query = query.join(Result).filter(Result.semester == selected_sem)
        
    students = query.all()
    return render_template('index.html', students=students, divisions=divisions, selected_div=selected_div, selected_sem=selected_sem)

@app.route('/dashboard/<int:student_id>')
def dashboard(student_id):
    student = Student.query.get_or_404(student_id)
    selected_sem = request.args.get('semester', '')
    
    # Get available semesters for this student
    all_results = Result.query.filter_by(student_id=student.id).all()
    available_sems = sorted(list(set([r.semester for r in all_results])))
    
    if not selected_sem and available_sems:
        selected_sem = available_sems[-1] # Default to latest
        
    results = Result.query.filter_by(student_id=student.id, semester=selected_sem).all()
    
    # Calculations
    total_marks_obtained = sum([r.total_marks for r in results])
    total_max_marks = sum([r.subject.max_marks for r in results])
    percentage = (total_marks_obtained / total_max_marks * 100) if total_max_marks > 0 else 0
    
    total_credits = 0
    total_grade_points = 0
    is_fail = False
    
    chart_labels = []
    chart_total_marks = []
    chart_ut_marks = []
    chart_mse_marks = []
    
    for r in results:
        grade, gp = r.grade_info
        total_credits += r.subject.credits
        total_grade_points += r.subject.credits * gp
        if grade == 'F':
            is_fail = True
            
        chart_labels.append(r.subject.subject_code)
        chart_total_marks.append(r.total_marks)
        chart_ut_marks.append(r.ut_marks)
        chart_mse_marks.append(r.mse_marks)
            
    sgpa = (total_grade_points / total_credits) if total_credits > 0 else 0
    result_status = "FAIL" if is_fail else "PASS"
    
    charts_data = {
        "labels": chart_labels,
        "totals": chart_total_marks,
        "uts": chart_ut_marks,
        "mses": chart_mse_marks
    }
    
    return render_template(
        'dashboard.html', 
        student=student, 
        results=results, 
        semester=selected_sem,
        available_sems=available_sems,
        summary={
            "total_obtained": total_marks_obtained,
            "total_max": total_max_marks,
            "percentage": round(percentage, 2),
            "sgpa": round(sgpa, 2),
            "status": result_status
        },
        charts_data=charts_data
    )

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash("No file part")
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            flash("No selected file")
            return redirect(request.url)
        
        semester = request.form.get('semester')
        if not semester:
            flash("Please specify a semester")
            return redirect(request.url)
            
        if file and file.filename.endswith(('.xlsx', '.xls')):
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(file.filename))
            file.save(filepath)
            
            try:
                process_excel(filepath, semester)
                flash(f"Data imported successfully for Semester {semester}!")
                return redirect(url_for('index'))
            except Exception as e:
                flash(f"Error processing file: {str(e)}")
                db.session.rollback()
                return redirect(request.url)
                
    return render_template('upload.html')

def process_excel(filepath, semester):
    """
    Expects Wide Format:
    PRN | Name | Division | SubjectCode | SubjectName | Credits | MaxMarks | Assignment | Attendance | UT | MSE
    (If multiple subjects per row, we can unpivot it, or if it's long format, process line by line.
     We will expect a slightly simplified flattened format for the sample or pivot.)
     
    Wait, the rules say "Do NOT mix subjects in columns (must be normalized)".
    If the input Excel is wide (like the image, e.g. Subject 1 Assign, Atten, UT, MSE | Subject 2 Assign, Atten, UT, MSE),
    we need to parse it. Let's assume the Excel has headers like:
    PRN, Name, Division, SubCode_Assign, SubCode_Atten, SubCode_UT, SubCode_MSE
    But to make it robust and easy, let's assume a simpler normalized Excel import:
    Columns: PRN, Name, Division, SubjectCode, SubjectName, Credits, MaxMarks, Assignment, Attendance, UT, MSE
    The prompt says: "Convert Excel (wide format) into normalized database entries".
    So the excel WILL be wide format!
    Wait, if the user uploaded an Excel that's wide format, how do we know the subject codes?
    Let's handle dynamic wide format reading:
    PRN | Name | Division | Sub1_Code | Sub1_Name | Sub1_Credits | Sub1_Assign | Sub1_Atten | Sub1_UT | Sub1_MSE | Sub2_Code ...
    OR
    A common wide format:
    PRN, Name, Division, 
    Maths_Assignment, Maths_Attendance, Maths_UT, Maths_MSE, 
    Physics_Assignment, Physics_Attendance, Physics_UT, Physics_MSE...
    
    Let's extract subject names from the columns by splitting by '_' .
    """
    df = pd.read_excel(filepath)
    # Fill NaN with 0 for marks
    df = df.fillna(0)
    
    for index, row in df.iterrows():
        prn = str(row.get('PRN', '')).strip()
        name = str(row.get('Name', '')).strip()
        division = str(row.get('Division', '')).strip()
        
        if not prn or not name:
            continue # Skip empty rows
            
        # 1. Create or get student
        student = Student.query.filter_by(prn=prn).first()
        if not student:
            if division not in ['A', 'B', 'C', 'D']:
                division = 'A' # fallback
            student = Student(prn=prn, name=name, division=division)
            db.session.add(student)
            db.session.commit()
            
        # 2. Extract subjects and marks from wide columns
        # E.g. columns might be CS101_Assignment, CS101_Attendance, CS101_UT, CS101_MSE
        subjects_found = {}
        
        for col in df.columns:
            if '_' in col:
                parts = col.split('_')
                sub_code = parts[0]
                mark_type = parts[1].lower() # assignment, attendance, ut, mse
                
                if mark_type in ['assignment', 'attendance', 'ut', 'mse']:
                    if sub_code not in subjects_found:
                        subjects_found[sub_code] = {'Assignment': 0, 'Attendance': 0, 'UT': 0, 'MSE': 0}
                    subjects_found[sub_code][mark_type.capitalize()] = row[col]

        for sub_code, marks in subjects_found.items():
            # Create or get subject. We'll use dummy credits/name if new.
            subject = Subject.query.filter_by(subject_code=sub_code).first()
            if not subject:
                subject = Subject(subject_code=sub_code, subject_name=f"Subject {sub_code}", credits=3, max_marks=60)
                db.session.add(subject)
                db.session.commit()
                
            # Create or get result
            result = Result.query.filter_by(student_id=student.id, subject_id=subject.id, semester=semester).first()
            if not result:
                result = Result(student_id=student.id, subject_id=subject.id, semester=semester)
                db.session.add(result)
                
            try:
                result.assignment_marks = float(marks.get('Assignment', 0))
                result.attendance_marks = float(marks.get('Attendance', 0))
                result.ut_marks = float(marks.get('Ut', 0))
                result.mse_marks = float(marks.get('Mse', 0))
            except ValueError:
                pass

    db.session.commit()

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5000)
