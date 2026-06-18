import os
os.environ.setdefault('SECRET_KEY', 'placeholder_secret_key_for_testing_purposes_only_32_chars')
os.environ.setdefault('JWT_SECRET_KEY', 'placeholder_jwt_secret_key_for_testing_purposes_only_32_chars')

import pytest
from app import create_app
from extensions import db as _db
from config import Config
import factory
from faker import Faker
from models.student import Student
from models.faculty import Faculty
from models.attendance import Attendance

fake = Faker()

# FIX: Use StaticPool and check_same_thread=False for SQLite in-memory database to prevent schema isolation across connection scopes
from sqlalchemy.pool import StaticPool

class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:' # Use in-memory for speed
    SQLALCHEMY_ENGINE_OPTIONS = {
        'poolclass': StaticPool,
        'connect_args': {'check_same_thread': False}
    }
    WTF_CSRF_ENABLED = False # Disable CSRF for testing convenience unless explicitly testing it
    REDIS_URL = "redis://localhost:6379/1"

@pytest.fixture(scope='session')
def app():
    app = create_app(TestConfig)
    return app

@pytest.fixture(scope='session', autouse=True)
def db(app):
    with app.app_context():
        _db.create_all()
        yield _db
        _db.drop_all()

@pytest.fixture(scope='function')
def session(db):
    db.session.begin_nested()
    yield db.session
    db.session.rollback()
    db.session.remove()

@pytest.fixture
def client(app):
    return app.test_client()

# Factories
class StudentFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = Student
        sqlalchemy_session_persistence = 'commit'

    roll = factory.LazyAttribute(lambda _: fake.unique.bothify(text='??-####'))
    name = factory.LazyAttribute(lambda _: fake.name())
    email = factory.LazyAttribute(lambda _: fake.unique.email())
    department = "Computer"
    division = "A"
    year = "TY"

class FacultyFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = Faculty
        sqlalchemy_session_persistence = 'commit'

    name = factory.LazyAttribute(lambda _: fake.name())
    email = factory.LazyAttribute(lambda _: fake.unique.email())
    department = "Computer"

@pytest.fixture
def student(session):
    StudentFactory._meta.sqlalchemy_session = session
    return StudentFactory()

@pytest.fixture
def faculty(session):
    FacultyFactory._meta.sqlalchemy_session = session
    return FacultyFactory()

# Mock Fixtures
@pytest.fixture
def mock_redis(mocker):
    return mocker.patch("extensions.redis_client")

@pytest.fixture
def mock_sms(mocker):
    return mocker.patch("utils.comm_utils.send_sms")
