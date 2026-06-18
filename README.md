# DY Patil University ERP System

A robust, modularized management system for educational institutions. This platform handles everything from student enrollment to attendance tracking and results management.

## 🚀 Key Features

- **Attendance Management**: supports manual entry and batch uploads from PDF/Excel reports.
- **Results Dashboard**: Automated grade calculation (`PASS/FAIL/ATKT`) based on university standards.
- **Role-Based Access**: Specialized dashboards for Admins, Faculty, and Students.
- **Advanced Analytics**: Real-time stats for attendance and academic performance.
- **Audit Logging**: tracks sensitive administrative actions for security.
- **Notification System**: Broadcast announcements to specific roles or the entire university.

## 🏗 Project Structure (Refactored)

The project follows a modular architecture for scalability:

- `app.py`: Main entry point and Flask application factory.
- `config.py`: Centralized configuration and constants.
- `routes/`: Blueprint-based modular routing (Attendance, Results, Cumulative, Features).
- `utils/`: Core utilities including the PostgreSQL database wrapper and shared helpers.
- `services/`: Business logic for complex operations (Excel/PDF parsing, report generation).
- `models/`: Database schema definitions and model logic.
- `templates/`: Categorized UI views organized by domain (Admin, Faculty, Student, etc.).
- `static/`: Frontend assets (CSS, JS, Images).

## 🛠 Tech Stack

- **Backend**: Python, Flask
- **Database**: PostgreSQL
- **Parsing**: `pdfplumber`, `openpyxl`
- **Security**: PBKDF2 Password Hashing, CSRF Protection

## ⚠️ Production startup
Always start with: gunicorn --config gunicorn.conf.py "app:create_app()"
Never use: python app.py in production.

## ⚙️ Setup & Installation

1. **Clone the repository**:
   ```bash
   git clone <your-repo-url>
   cd <project-folder>
   ```

2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Environment**:
   Set your PostgreSQL connection string in the environment:
   ```bash
   export DATABASE_URL="postgresql://user:password@localhost:5432/dbname"
   ```

4. **Run the Application**:
   ```bash
   python app.py
   ```

## 📸 Screenshots

### Login Page
![Login Page](static/images/login_screenshot.png)

### Admissions Dashboard
![Admissions Dashboard](static/images/dashboard_screenshot.png)

## 👤 Developer Details

- **Name**: Abhay Varvate (Anhay Varvate)
- **Email**: [sirabhi618@gmail.com](mailto:sirabhi618@gmail.com)
- **GitHub**: [@abhicodess](https://github.com/abhicodess)

## 🧹 Maintenance & Scripts
The project includes an `archive/` folder containing legacy migration scripts for reference. New features should be added to the appropriate `routes/` or `services/` modules.
