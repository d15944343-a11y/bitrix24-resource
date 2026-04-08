import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.__init__ import create_app
from app.extensions import db
from app.ml import ensure_demo_assets_registered
from app.seeds import seed_clients_data, seed_roles_and_users


@pytest.fixture()
def app():
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        }
    )

    with app.app_context():
        db.drop_all()
        db.create_all()
        ensure_demo_assets_registered()
        seed_roles_and_users()
        seed_clients_data()

    app.config.update(
        TESTING=True,
    )
    return app


@pytest.fixture()
def client(app):
    return app.test_client()
