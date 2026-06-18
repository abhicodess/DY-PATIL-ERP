import marshmallow as ma

class SubjectResultSchema(ma.Schema):
    subject_code        = ma.fields.Str(required=True)
    subject_name        = ma.fields.Str(required=True)
    internal_marks      = ma.fields.Float(required=True)
    external_marks      = ma.fields.Float(required=True)
    total               = ma.fields.Float(required=True)
    grade               = ma.fields.Str(required=True)
    is_published        = ma.fields.Bool(load_default=False)

class ResultResponseSchema(ma.Schema):
    id                  = ma.fields.Int()
    student_id          = ma.fields.Int()
    semester            = ma.fields.Str()
    subject_id          = ma.fields.Int()
    internal_marks      = ma.fields.Float()
    external_marks      = ma.fields.Float()
    total               = ma.fields.Float()
    grade               = ma.fields.Str()
    is_published        = ma.fields.Bool()

class MarksheetSchema(ma.Schema):
    student_id          = ma.fields.Int(required=True)
    student_name        = ma.fields.Str()
    roll                = ma.fields.Str()
    semester            = ma.fields.Str(required=True)
    results             = ma.fields.List(ma.fields.Nested(SubjectResultSchema))
    gpa                 = ma.fields.Float()

class ResultUploadSchema(ma.Schema):
    semester            = ma.fields.Str(required=True)
    subject_code        = ma.fields.Str(required=True)
    exam_type           = ma.fields.Str(required=True, validate=ma.validate.OneOf(['Internal', 'External', 'Semester Exam']))
    file_key            = ma.fields.Str(required=True)
