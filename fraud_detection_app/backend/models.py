from sqlalchemy import Column, Integer, String, DateTime, func
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id          = Column(Integer, primary_key=True, index=True)
    email       = Column(String, unique=True, index=True, nullable=False)
    hashed_pw   = Column(String, nullable=False)

    # ------------- NEW -------------
    name        = Column(String, nullable=False)
    age         = Column(Integer)
    gender      = Column(String(16))
    country     = Column(String(64))
    # --------------------------------

    created_at  = Column(DateTime(timezone=True), server_default=func.now())

