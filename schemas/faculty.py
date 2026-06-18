import marshmallow as ma

class FacultyCreateSchema(ma.Schema):
    name         = ma.fields.Str(required=True, validate=ma.validate.Length(min=2, max=100))
    email        = ma.fields.Email(required=True)
    department   = ma.fields.Str(required=True, validate=ma.validate.OneOf(
                    ['CS','IT','ENTC','MECH','CIVIL','AIDS','AIML']))
    designation  = ma.fields.Str(required=True)
    phone        = ma.fields.Str(validate=ma.validate.Regexp(r'^\+?[0-9]{10,13}$'))
    qualification = ma.fields.Str()

class FacultyResponseSchema(ma.Schema):
    id           = ma.fields.Int()
    name         = ma.fields.Str()
    email        = ma.fields.Str()
    department   = ma.fields.Str()
    designation  = ma.fields.Str()
    phone        = ma.fields.Str()
    qualification = ma.fields.Str()

class LeaveRequestSchema(ma.Schema):
    leave_type   = ma.fields.Str(required=True, validate=ma.validate.OneOf(['CL', 'SL', 'EL', 'ML']))
    from_date    = ma.fields.Date(required=True)
    to_date      = ma.fields.Date(required=True)
    reason       = ma.fields.Str(required=True, validate=ma.validate.Length(min=5, max=500))

class WorkloadSchema(ma.Schema):
    subject_code = ma.fields.Str(required=True)
    semester     = ma.fields.Str(required=True)
    weekly_hours = ma.fields.Int(required=True, validate=ma.validate.Range(min=1, max=20))
