from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from database import get_db
from models import User
import os
import hashlib

SECRET_KEY = os.getenv("SECRET_KEY", "a9F3kL2P0XcR7mWQ8HnEJZ4YbT6S1dV")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1440

# Use simple SHA256 hashing (no bcrypt issues)
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return hashlib.sha256(plain_password.encode()).hexdigest() == hashed_password

def get_password_hash(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer

security = HTTPBearer()

def get_current_user(
    credentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    token = credentials.credentials
    payload = decode_access_token(token)
    
    if payload is None:
        raise credentials_exception
    
    username: str = payload.get("sub")
    if username is None:
        raise credentials_exception
    
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise credentials_exception
    
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user")
    
    return user

def authenticate_user(db: Session, username: str, password: str) -> Optional[User]:
    user = db.query(User).filter(User.username == username).first()
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user

def create_default_user(db: Session):
    existing_user = db.query(User).filter(User.username == "admin").first()
    if not existing_user:
        default_user = User(
            username="admin",
            email="admin@ticket9ja.com",
            hashed_password=get_password_hash("admin123"),
            full_name="System Administrator",
            is_active=True
        )
        db.add(default_user)
        db.commit()
        print("✅ Default admin user created (username: admin, password: admin123)")
    else:
        print("ℹ️  Default admin user already exists")
