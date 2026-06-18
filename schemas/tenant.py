import marshmallow as ma

class TenantResponseSchema(ma.Schema):
    id          = ma.fields.Int()
    name        = ma.fields.Str()
    slug        = ma.fields.Str()
    schema_name = ma.fields.Str()
    created_at  = ma.fields.DateTime()
