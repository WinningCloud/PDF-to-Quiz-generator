from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from passlib.context import CryptContext

from quiz_platform.db.database import get_db
from quiz_platform.db import models

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


@router.post("/init-admin")
def create_initial_admin(db: Session = Depends(get_db)):
    # ⚠️ Prevent creating multiple admins
    existing_admin = db.query(models.User).filter(models.User.is_admin == True).first()
    if existing_admin:
        raise HTTPException(status_code=400, detail="Admin already exists")

    admin_user = models.User(
        email="admin@quizapp.com",
        username="admin",
        hashed_password=pwd_context.hash("admin123"),  # CHANGE AFTER LOGIN
        is_admin=True,
        is_active=True,
    )

    db.add(admin_user)
    db.commit()
    db.refresh(admin_user)

    return {"message": "Admin user created", "email": admin_user.email}
