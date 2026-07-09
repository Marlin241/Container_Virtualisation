import os

from sqlalchemy.orm import Session

from . import models
from .security import hash_password


def seed_admin(db: Session) -> None:
    admin_email = os.getenv("ADMIN_EMAIL")
    admin_password = os.getenv("ADMIN_PASSWORD")
    if not admin_email or not admin_password:
        return

    existing_admin = db.query(models.User).filter(models.User.role == models.UserRole.PERSONNEL_ADMIN).first()
    if existing_admin:
        return

    db.add(
        models.User(
            full_name="Administrateur",
            email=admin_email,
            password_hash=hash_password(admin_password),
            role=models.UserRole.PERSONNEL_ADMIN,
        )
    )
    db.commit()
