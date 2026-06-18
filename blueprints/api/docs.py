from flask import Flask
from flask_smorest import Api
from extensions import db

def init_api(app):
    app.config["API_TITLE"] = "DY Patil ERP API"
    app.config["API_VERSION"] = "v1"
    app.config["OPENAPI_VERSION"] = "3.0.2"
    app.config["OPENAPI_URL_PREFIX"] = "/api"
    app.config["OPENAPI_SWAGGER_UI_PATH"] = "/docs"
    app.config["OPENAPI_SWAGGER_UI_URL"] = "https://cdn.jsdelivr.net/npm/swagger-ui-dist/"
    
    api = Api(app)
    
    # We would register our Marshmallow-based blueprints here
    # from blueprints.api.v1.students import students_blp
    # api.register_blueprint(students_blp)
    
    return api
