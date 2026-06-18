from extensions import db
from sqlalchemy import text

class BaseRepository:
    def __init__(self, model):
        self.model = model

    def get_all(self):
        return self.model.query.all()

    def get_by_id(self, id):
        return self.model.query.get(id)

    def create(self, **kwargs):
        # Filter attributes for the model to prevent invalid keyword argument errors
        valid_keys = {c.name for c in self.model.__table__.columns}
        filtered_kwargs = {k: v for k, v in kwargs.items() if k in valid_keys}
        instance = self.model(**filtered_kwargs)
        db.session.add(instance)
        db.session.commit()
        return instance

    def update(self, id, **kwargs):
        instance = self.get_by_id(id)
        if instance:
            valid_keys = {c.name for c in self.model.__table__.columns}
            filtered_kwargs = {k: v for k, v in kwargs.items() if k in valid_keys}
            for key, value in filtered_kwargs.items():
                setattr(instance, key, value)
            db.session.commit()
        return instance

    def delete(self, id):
        instance = self.get_by_id(id)
        if instance:
            db.session.delete(instance)
            db.session.commit()
            return True
        return False

    def execute_raw(self, query, params=None):
        return db.session.execute(text(query), params or {})
