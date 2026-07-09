import pytest

from app import models
from app.seed import seed_admin
from tests.conftest import TestingSessionLocal


@pytest.fixture
def db():
    session = TestingSessionLocal()
    yield session
    session.close()


def test_seed_admin_noop_when_env_not_set(db, monkeypatch):
    monkeypatch.delenv("ADMIN_EMAIL", raising=False)
    monkeypatch.delenv("ADMIN_PASSWORD", raising=False)

    seed_admin(db)

    assert db.query(models.User).count() == 0


def test_seed_admin_creates_admin_when_env_set(db, monkeypatch):
    monkeypatch.setenv("ADMIN_EMAIL", "admin@dit.sn")
    monkeypatch.setenv("ADMIN_PASSWORD", "adminpass123")

    seed_admin(db)

    admin = db.query(models.User).filter(models.User.email == "admin@dit.sn").first()
    assert admin is not None
    assert admin.role == models.UserRole.PERSONNEL_ADMIN


def test_seed_admin_noop_when_admin_already_exists(db, monkeypatch):
    monkeypatch.setenv("ADMIN_EMAIL", "admin@dit.sn")
    monkeypatch.setenv("ADMIN_PASSWORD", "adminpass123")

    db.add(
        models.User(
            full_name="Existing Admin",
            email="existing-admin@dit.sn",
            password_hash="irrelevant",
            role=models.UserRole.PERSONNEL_ADMIN,
        )
    )
    db.commit()

    seed_admin(db)

    assert db.query(models.User).count() == 1
    assert db.query(models.User).first().email == "existing-admin@dit.sn"
