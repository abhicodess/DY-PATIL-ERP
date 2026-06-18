import marshmallow as ma

class LoginSchema(ma.Schema):
    username = ma.fields.Str(required=True)
    password = ma.fields.Str(required=True)
    role     = ma.fields.Str(required=True, validate=ma.validate.OneOf(['admin', 'faculty', 'student']))

class UserProfileSchema(ma.Schema):
    id         = ma.fields.Int()
    name       = ma.fields.Str()
    role       = ma.fields.Str()
    department = ma.fields.Str(allow_none=True)

class LoginResponseSchema(ma.Schema):
    access_token  = ma.fields.Str(required=True)
    refresh_token = ma.fields.Str(required=True)
    user          = ma.fields.Nested(UserProfileSchema, required=True)

class RefreshResponseSchema(ma.Schema):
    access_token  = ma.fields.Str(required=True)

class CSRFResponseSchema(ma.Schema):
    csrf_token    = ma.fields.Str(required=True)
