from repositories.base_repository import BaseRepository
from models.payroll import FacultySalary, Payslip

class PayrollRepository(BaseRepository):
    def __init__(self):
        super().__init__(FacultySalary)

    def get_salary_info(self, faculty_id):
        return FacultySalary.query.filter_by(faculty_id=faculty_id).first()

    def get_payslips(self, faculty_id):
        return Payslip.query.filter_by(faculty_id=faculty_id).order_by(Payslip.year.desc(), Payslip.month.desc()).all()
