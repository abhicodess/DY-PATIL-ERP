import marshmallow as ma

class ReportGenerateSchema(ma.Schema):
    report_type  = ma.fields.Str(required=True, validate=ma.validate.OneOf(['attendance', 'results', 'defaulters']))
    format       = ma.fields.Str(required=True, validate=ma.validate.OneOf(['pdf', 'xlsx', 'csv']))
    filters      = ma.fields.Dict(load_default={})

class ReportStatusSchema(ma.Schema):
    job_id       = ma.fields.Str(required=True)
    status       = ma.fields.Str(required=True, validate=ma.validate.OneOf(['pending', 'processing', 'done', 'failed']))
    progress     = ma.fields.Int(load_default=0)
    download_url = ma.fields.Str(allow_none=True)
    error        = ma.fields.Str(allow_none=True)

class ReportHistorySchema(ma.Schema):
    id           = ma.fields.Int()
    report_type  = ma.fields.Str()
    format       = ma.fields.Str()
    created_at   = ma.fields.DateTime()
    status       = ma.fields.Str()
