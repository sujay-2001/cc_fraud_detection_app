from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from models import User
from auth import get_current_user, get_db
from pydantic import BaseModel

router_clients = APIRouter(prefix="/clients", tags=["clients"])

class ClientOut(BaseModel):
    email: str
    name: str
    age: int | None = None
    gender: str | None = None
    country: str | None = None

    class Config:
        from_attributes = True


@router_clients.get("/me", response_model=ClientOut)
def get_me(user_email: str = Depends(get_current_user),
           db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == user_email).first()
    if not user:
        raise HTTPException(404, "User not found")
    return user
