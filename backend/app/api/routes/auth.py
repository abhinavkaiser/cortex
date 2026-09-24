from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User

router = APIRouter(prefix="/api/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str = ""


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    # needs_onboarding used to signal "no track assigned yet -> show the
    # onboarding flow". Onboarding/tracks are gone (see
    # frontend/app/onboarding, removed) -- a new user now lands straight on
    # the course catalog, same as everyone else, so there's nothing left
    # for this field to signal.


@router.post("/register", response_model=TokenResponse)
def register(body: RegisterRequest, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == body.email).first():
        raise HTTPException(409, "Email already registered")
    user = User(email=body.email, hashed_password=hash_password(body.password), full_name=body.full_name)
    db.add(user)
    db.commit()
    db.refresh(user)
    return TokenResponse(access_token=create_access_token(user.id), user_id=user.id)


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == body.email).first()
    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(401, "Invalid email or password")
    return TokenResponse(access_token=create_access_token(user.id), user_id=user.id)
