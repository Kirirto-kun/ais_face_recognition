from sqlalchemy import Column, Integer, String, DateTime, Date, Time, Boolean
from sqlalchemy.sql import func
from .database import Base

class Attendance(Base):
    __tablename__ = "attendance"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    time = Column(Time)
    date = Column(Date)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password = Column(String)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

# Pydantic models for request/response
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime, date

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

class UserBase(BaseModel):
    username: str
    email: Optional[EmailStr] = None
    is_active: Optional[bool] = True

class UserCreate(UserBase):
    password: str

class UserInDB(UserBase):
    id: int
    created_at: datetime

    class Config:
        orm_mode = True

class LoginRequest(BaseModel):
    username: str
    password: str

class NameRequest(BaseModel):
    name1: str
    name2: Optional[str] = None

class AttendanceRecord(BaseModel):
    name: str
    time: str
    date: str

    class Config:
        orm_mode = True

class UserSession(BaseModel):
    username: str
    logged_in: bool 