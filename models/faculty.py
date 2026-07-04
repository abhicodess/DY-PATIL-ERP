from extensions import db

class Faculty(db.Model):
    __tablename__ = 'faculty'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    department = db.Column(db.String(100), nullable=False)
    designation = db.Column(db.String(100))
    email = db.Column(db.String(120), nullable=False, unique=True)
    phone = db.Column(db.String(20))
    qualification = db.Column(db.String(150))
    joining_date = db.Column(db.String(50))
    password = db.Column(db.String(255), default='faculty123')
    photo = db.Column(db.String(255), default='')
    must_change_password = db.Column(db.Boolean, default=False, server_default='0')
    employee_id = db.Column(db.String(100), nullable=True)
    is_active = db.Column(db.Boolean, default=True)

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}
