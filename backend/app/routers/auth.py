from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from ..auth import hash_password, verify_password, create_token, get_db, get_current_user
from ..config import BONUS_CHIPS, REGISTER_RATE_LIMIT
from ..db import User, normalize_handle
from ..games import fair
from ..ratelimit import RateLimiter, client_ip

router = APIRouter(prefix="/api/auth", tags=["auth"])

register_limit = RateLimiter(*REGISTER_RATE_LIMIT)
login_limit = RateLimiter(10, 60)


class RegisterIn(BaseModel):
    email: EmailStr
    password: str
    username: str | None = None


class LoginIn(BaseModel):
    email: EmailStr
    password: str


def _pick_username(db: Session, raw: str | None, email: str) -> str:
    base = normalize_handle(raw) if raw else normalize_handle(email.split("@")[0])
    name, n = base, 1
    while db.query(User).filter(User.username == name).first():
        name, n = f"{base}{n}", n + 1
    return name


def _public(user: User) -> dict:
    return {
        "id": user.id,
        "username": user.username or f"player_{user.id}",
        "email": user.email,
        "chips": user.chips,
    }


@router.post("/register")
def register(body: RegisterIn, request: Request, db: Session = Depends(get_db)):
    if not register_limit.allowed(client_ip(request)):
        raise HTTPException(status_code=429, detail="Too many accounts from this IP", headers={"Retry-After": "3600"})
    if len(body.password) < 6:
        raise HTTPException(status_code=400, detail="Password too short (min 6 chars)")
    if db.query(User).filter(User.email == body.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    user = User(
        email=body.email,
        username=_pick_username(db, body.username, body.email),
        password_hash=hash_password(body.password),
        chips=BONUS_CHIPS,
    )
    user.server_seed = fair.gen_seed()
    user.server_seed_commit = fair.hash_hex(user.server_seed)
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"token": create_token(user.id), "user": _public(user)}


@router.post("/login")
def login(body: LoginIn, request: Request, db: Session = Depends(get_db)):
    if not login_limit.allowed(client_ip(request)):
        raise HTTPException(
            status_code=429,
            detail="Too many login attempts, try later",
            headers={"Retry-After": "60"},
        )
    user = db.query(User).filter(User.email == body.email).first()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"token": create_token(user.id), "user": _public(user)}


@router.get("/me")
def me(user: User = Depends(get_current_user)):
    return _public(user)