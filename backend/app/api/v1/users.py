"""Internal API v1 — User management endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.core.security import hash_password

router = APIRouter(tags=["users"])


@router.get("/users")
def list_users(
    db: Session = Depends(get_db),
):
    users = db.query(User).filter(User.is_active == True).all()
    return [{
        "id": str(u.id),
        "username": u.username,
        "email": u.email,
        "role": u.role,
        "display_name": u.display_name,
        "is_active": u.is_active,
        "created_at": u.created_at.isoformat() if u.created_at else None,
    } for u in users]


@router.post("/users")
def create_user(
    payload: dict,
    db: Session = Depends(get_db),
):
    user = User(
        username=payload["username"],
        email=payload.get("email", ""),
        role=payload.get("role", "consultant"),
        display_name=payload.get("display_name", payload.get("full_name", "")),
        hashed_password=hash_password(payload["password"]),
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.get("/users/{user_id}")
def get_user(user_id: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.put("/users/{user_id}")
def update_user(user_id: str, payload: dict, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    for key in ("username", "email", "role", "display_name"):
        if key in payload:
            setattr(user, key, payload[key])
    if "password" in payload:
        user.hashed_password = hash_password(payload["password"])
    db.commit()
    return user
