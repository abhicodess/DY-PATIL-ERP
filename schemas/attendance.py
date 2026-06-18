import marshmallow as ma
from schemas.common import PaginationSchema

class AttendanceRecordSchema(ma.Schema):
    student_id   = ma.fields.Int(required=True)
    status       = ma.fields.Str(required=True, validate=ma.validate.OneOf(['Present', 'Absent', 'Late', 'Excused', 'Leave']))
    remark       = ma.fields.Str(load_default="")

class AttendanceSubmitSchema(ma.Schema):
    subject      = ma.fields.Str(required=True)
    date         = ma.fields.Date(required=True)
    time_slot    = ma.fields.Str(required=True)
    division     = ma.fields.Str(required=True)
    semester     = ma.fields.Str(required=True)
    records      = ma.fields.List(ma.fields.Nested(AttendanceRecordSchema), required=True)

class AttendanceQuerySchema(PaginationSchema):
    student_id   = ma.fields.Int()
    subject      = ma.fields.Str()
    start_date   = ma.fields.Date()
    end_date     = ma.fields.Date()

class AttendanceSummarySchema(ma.Schema):
    student_id   = ma.fields.Int()
    student_name = ma.fields.Str()
    subject      = ma.fields.Str()
    attended     = ma.fields.Int()
    total        = ma.fields.Int()
    percentage   = ma.fields.Float()
