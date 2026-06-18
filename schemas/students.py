import marshmallow as ma
from schemas.common import PaginationSchema, SortSchema

class StudentCreateSchema(ma.Schema):
    name         = ma.fields.Str(required=True, validate=ma.validate.Length(min=2, max=100))
    email        = ma.fields.Email(required=True)
    roll         = ma.fields.Str(required=True, metadata={"example": "CS2024001"})
    department   = ma.fields.Str(required=True, validate=ma.validate.OneOf(
                    ['CS','IT','ENTC','MECH','CIVIL','AIDS','AIML']))
    year         = ma.fields.Int(required=True, validate=ma.validate.Range(min=1, max=4))
    division     = ma.fields.Str(required=True, validate=ma.validate.OneOf(['A','B','C','D']))
    semester     = ma.fields.Int(required=True, validate=ma.validate.Range(min=1, max=8))
    dob          = ma.fields.Date(required=True)
    phone        = ma.fields.Str(validate=ma.validate.Regexp(r'^\+?[0-9]{10,13}$'))
    parent_phone = ma.fields.Str(validate=ma.validate.Regexp(r'^\+?[0-9]{10,13}$'))
    address      = ma.fields.Str(validate=ma.validate.Length(max=500))

class StudentUpdateSchema(ma.Schema):
    name         = ma.fields.Str(validate=ma.validate.Length(min=2, max=100))
    email        = ma.fields.Email()
    phone        = ma.fields.Str()
    address      = ma.fields.Str()

class StudentResponseSchema(ma.Schema):
    id           = ma.fields.Int()
    name         = ma.fields.Str()
    email        = ma.fields.Str()
    roll         = ma.fields.Str()
    department   = ma.fields.Str()
    year         = ma.fields.Int()
    division     = ma.fields.Str()
    semester     = ma.fields.Int()
    phone        = ma.fields.Str()
    attendance_pct = ma.fields.Float(metadata={"description": "Current month attendance %"}, load_default=0.0)
    created_at   = ma.fields.DateTime()

class StudentListQuerySchema(PaginationSchema, SortSchema):
    department  = ma.fields.Str()
    year        = ma.fields.Int()
    division    = ma.fields.Str()
    search      = ma.fields.Str(metadata={"description": "Search by name or roll number"})
    min_attendance = ma.fields.Float(metadata={"description": "Filter by min attendance %"})
