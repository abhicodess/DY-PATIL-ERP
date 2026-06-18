from repositories.payroll_repository import PayrollRepository

class PayrollService:
    def __init__(self):
        self.repository = PayrollRepository()

    def calculate_monthly_salary(self, faculty_id):
        sal = self.repository.get_salary_info(faculty_id)
        if not sal: return 0
        
        gross = sal.basic_salary + sal.hra + sal.da
        net = gross - sal.pf_deduction
        return {
            'gross': gross,
            'net': net,
            'pf': sal.pf_deduction
        }

    def generate_payslip(self, faculty_id, month, year):
        totals = self.calculate_monthly_salary(faculty_id)
        # Logic to save to Payslip table and generate PDF
        return totals
