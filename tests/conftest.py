import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'nhl-dashboard', 'backend'))


@pytest.fixture
def app():
    """Create Flask test app with in-memory SQLite."""
    from app import create_app

    return create_app({'TESTING': True, 'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:'})


@pytest.fixture
def client(app):
    """Flask test client."""
    return app.test_client()
