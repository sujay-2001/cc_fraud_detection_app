from fastapi import Request, APIRouter, HTTPException, Depends, Header, Body, BackgroundTasks
from sqlalchemy.orm import Session
from passlib.hash import bcrypt
from jose import jwt
from pydantic import BaseModel, EmailStr, Field
import os

from models import User, Base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from otp_utils import (
    generate_code, send_code_email, can_request,
    remember_code, consume_code, is_verified, send_welcome_email, r
)

SECRET_KEY = "change-me"   # move into env in prod
ALGORITHM  = "HS256"

DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine, autoflush=False)

Base.metadata.create_all(engine)

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
        
# ───────── request schemas ─────────
class EmailPayload(BaseModel):
    email: EmailStr

class VerifyPayload(BaseModel):
    email: EmailStr
    otp: str

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    name: str
    age: int | None = None
    gender: str | None = None
    country: str | None = None

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

@router.post("/send-otp", status_code=200)
def send_otp(body: EmailPayload):
    email = body.email               # already validated
    if not can_request(email):
        raise HTTPException(429, "Too many OTP requests, try later")

    code = generate_code()
    remember_code(email, code)
    try:
        send_code_email(email, code)
    except Exception as exc:
        r.delete(f"otp:{email}")      # let user retry immediately
        raise HTTPException(500, f"Could not send e-mail: {exc}") from exc
    return {"msg": "code_sent"}


@router.post("/verify-otp", status_code=200)
def verify_otp(body: VerifyPayload):
    if consume_code(body.email, body.otp):
        return {"msg": "verified"}
    raise HTTPException(400, "Invalid or expired code")

@router.post("/register", status_code=201)
def register(payload: RegisterRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    if not is_verified(payload.email):
        raise HTTPException(400, "Email not verified")

    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(400, "User already exists")

    # optional: server-side password strength check (same zxcvbn lib)
    from zxcvbn import zxcvbn
    if zxcvbn(payload.password)["score"] < 2:
        raise HTTPException(400, "Weak password")

    user = User(
        email=payload.email,
        hashed_pw=bcrypt.hash(payload.password),
        name=payload.name,
        age=payload.age,
        gender=payload.gender,
        country=payload.country,
    )
    db.add(user)
    db.commit()
    background_tasks.add_task(send_welcome_email, user.email, user.name)
    return {"msg": "registered"}

@router.post("/login")
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not bcrypt.verify(payload.password, user.hashed_pw):
        raise HTTPException(401, "Invalid credentials")
    token = jwt.encode({"sub": user.email}, SECRET_KEY, algorithm=ALGORITHM)
    return {"access_token": token, "token_type": "bearer"}

def get_current_user(
    request: Request,
    authorization: str | None = Header(None)
) -> str:
    if not authorization:
        raise HTTPException(401, "Missing token")
    token = authorization.split(" ")[1]
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    email = payload["sub"]
    request.state.user = email          # <- NEW
    return email
