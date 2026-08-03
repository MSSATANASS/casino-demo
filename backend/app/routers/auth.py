from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from ..auth import hash_password, verify_password, create_token, get_db, get_current_user
from ..config import BONUS_CHIPS
from ..db import User

router = APIRouter(prefix="/api/auth", tags=["auth"])


class RegisterIn(BaseModel):
    email: EmailStr
    password: str


class LoginIn(BaseModel):
    email: EmailStr
    password: str


def _public(user: User) -> dict:
    return {"id": user.id, "email": user.email, "chips": user.chips}


@router.post("/register")
def register(body: RegisterIn, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == body.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    user = User(email=body.email, password_hash=hash_password(body.password), chips=BONUS_CHIPS)
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"token": create_token(user.id), "user": _public(user)}


@router.post("/login")
def login(body: LoginIn, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == body.email).first()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"token": create_token(user.id), "user": _public(user)}


@router.get("/me")
def me(user: User = Depends(get_current_user)):
    return _public(user)