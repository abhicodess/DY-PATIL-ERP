from extensions import db

class Student(db.Model):
    __tablename__ = 'students'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    roll = db.Column(db.String(50), nullable=False, unique=True)
    department = db.Column(db.String(100), nullable=False)
    year = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(120))
    password = db.Column(db.String(255), default='student123')
    photo = db.Column(db.String(255), default='')
    division = db.Column(db.String(50), default='')
    prn = db.Column(db.String(100), nullable=True)
    must_change_password = db.Column(db.Boolean, default=False, server_default='0')
    dob = db.Column(db.Date)
    gender = db.Column(db.String(50))
    contact_number = db.Column(db.String(50))
    parent_contact = db.Column(db.String(50))
    address = db.Column(db.Text)
    admission_year = db.Column(db.Integer)
    is_active = db.Column(db.Boolean, default=True)

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}
