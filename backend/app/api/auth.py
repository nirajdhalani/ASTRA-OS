from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import User
from ..schemas import AuthOutput, LoginInput, RegisterInput, UserOutput
from ..security import create_access_token, current_user, hash_password, verify_password

router = APIRouter(prefix="/api/auth", tags=["authentication"])


def _auth_output(user: User) -> AuthOutput:
    return AuthOutput(access_token=create_access_token(user.id), user=UserOutput(id=user.id, email=user.email, locale=user.locale, plan=user.plan))


@router.post("/register", response_model=AuthOutput, status_code=201)
def register(payload: RegisterInput, db: Session = Depends(get_db)):
    email = payload.email.strip().lower()
    existing = db.scalar(select(User).where(User.email == email))
    if existing:
        raise HTTPException(status_code=409, detail="An account with this email already exists")
    user = User(email=email, password_hash=hash_password(payload.password), locale=payload.locale)
    db.add(user)
    db.commit()
    db.refresh(user)
    return _auth_output(user)


@router.post("/login", response_model=AuthOutput)
def login(payload: LoginInput, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == payload.email.strip().lower()))
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Email or password is incorrect")
    return _auth_output(user)


@router.get("/me", response_model=UserOutput)
def me(user: User = Depends(current_user)):
    return UserOutput(id=user.id, email=user.email, locale=user.locale, plan=user.plan)
