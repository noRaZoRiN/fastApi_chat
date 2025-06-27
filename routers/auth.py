from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import List

from models import User, UserCreate, UserResponse, Token, fake_users_db, UserDB, NotificationResponse, NotificationDB
from dependencies import create_jwt_token, authenticate_user, get_password_hash, get_current_user
from database import get_db

router = APIRouter(prefix="/auth", tags=["Auth"])

@router.post("/register", response_model=UserResponse)
async def register(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(UserDB).filter(UserDB.username == user.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    
    if user.email:
        db_email = db.query(UserDB).filter(UserDB.email == user.email).first()
        if db_email:
            raise HTTPException(status_code=400, detail="Email already registered")
    
    hashed_password = get_password_hash(user.password)
    db_user = UserDB(username=user.username, password=hashed_password, email=user.email)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = authenticate_user(db, form_data.username, form_data.password)
    
    if not user:
        if form_data.username in fake_users_db and fake_users_db[form_data.username]["password"] == form_data.password:
            token = create_jwt_token({"sub": form_data.username})
            return {"access_token": token, "token_type": "bearer"}
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = create_jwt_token({"sub": user.username})
    return {"access_token": token, "token_type": "bearer"}

@router.get("/me", response_model=UserResponse)
async def read_users_me(current_user: UserDB = Depends(get_current_user)):
    if isinstance(current_user, str):
        raise HTTPException(status_code=400, detail="")
    return current_user

@router.get("/notifications", response_model=List[NotificationResponse])
async def get_notifications(current_user: UserDB = Depends(get_current_user), db: Session = Depends(get_db)):
    if isinstance(current_user, str):
        raise HTTPException(status_code=400, detail="")
    
    notifications = db.query(NotificationDB).filter(NotificationDB.user_id == current_user.id).order_by(NotificationDB.timestamp.desc()).all()
    return notifications

@router.put("/notifications/{notification_id}/read")
async def mark_notification_read(notification_id: int, current_user: UserDB = Depends(get_current_user), db: Session = Depends(get_db)):
    if isinstance(current_user, str):
        raise HTTPException(status_code=400, detail="")
    
    notification = db.query(NotificationDB).filter(
        NotificationDB.id == notification_id,
        NotificationDB.user_id == current_user.id
    ).first()
    
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    notification.is_read = True
    db.commit()
    return {"status": "success"}
