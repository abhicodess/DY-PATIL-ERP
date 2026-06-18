import marshmallow as ma

class PaginationSchema(ma.Schema):
    page      = ma.fields.Int(load_default=1, metadata={"description": "Page number (1-indexed)"})
    per_page  = ma.fields.Int(load_default=20, validate=ma.validate.Range(max=100),
                              metadata={"description": "Results per page, max 100"})

class PaginatedResponseSchema(ma.Schema):
    data      = ma.fields.List(ma.fields.Dict())
    total     = ma.fields.Int()
    page      = ma.fields.Int()
    per_page  = ma.fields.Int()
    pages     = ma.fields.Int()
    has_next  = ma.fields.Bool()
    has_prev  = ma.fields.Bool()

class ErrorSchema(ma.Schema):
    error   = ma.fields.Str(metadata={"example": "Not found"})
    code    = ma.fields.Str(metadata={"example": "STUDENT_NOT_FOUND"})
    details = ma.fields.Dict(load_default=None)

class ApiResponseSchema(ma.Schema):
    status  = ma.fields.Str(metadata={"example": "success"})
    data    = ma.fields.Raw()
    error   = ma.fields.Nested(ErrorSchema, load_default=None)
    meta    = ma.fields.Dict(load_default=None)

class SortSchema(ma.Schema):
    sort_by  = ma.fields.Str(load_default='created_at')
    order    = ma.fields.Str(validate=ma.validate.OneOf(['asc','desc']),
                            load_default='desc')
