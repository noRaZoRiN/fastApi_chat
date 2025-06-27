from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session
from typing import List

from models import Message, MessageResponse, UserDB, MessageDB
from dependencies import get_current_user
from database import get_db
from utils.manager import manager

router = APIRouter(prefix="/messages", tags=["Messages"])

@router.get("", response_model=List[MessageResponse])
async def get_user_messages(current_user: UserDB = Depends(get_current_user), db: Session = Depends(get_db)):
    if isinstance(current_user, str):
        raise HTTPException(status_code=400, detail="")
    
    messages = db.query(MessageDB).filter(
        ((MessageDB.sender_id == current_user.id) | (MessageDB.recipient_id == current_user.id)) &
        (MessageDB.group_id == None)
    ).order_by(MessageDB.timestamp).all()
    
    return messages

@router.get("/with/{user_id}", response_model=List[MessageResponse])
async def get_messages_with_user(
    user_id: int,
    current_user: UserDB = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if isinstance(current_user, str):
        raise HTTPException(status_code=400, detail="")
    
    other_user = db.query(UserDB).filter(UserDB.id == user_id).first()
    if not other_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    messages = db.query(MessageDB).filter(
        (
            ((MessageDB.sender_id == current_user.id) & (MessageDB.recipient_id == user_id)) |
            ((MessageDB.sender_id == user_id) & (MessageDB.recipient_id == current_user.id))
        ) &
        (MessageDB.group_id == None)
    ).order_by(MessageDB.timestamp).all()
    
    return messages

@router.post("/to/{recipient_id}", response_model=MessageResponse)
async def send_message(
    recipient_id: int,
    message: Message,
    current_user: UserDB = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if isinstance(current_user, str):
        raise HTTPException(status_code=400, detail="")
    
    recipient = db.query(UserDB).filter(UserDB.id == recipient_id).first()
    if not recipient:
        raise HTTPException(status_code=404, detail="Recipient not found")
    
    db_message = MessageDB(
        content=message.content,
        sender_id=current_user.id,
        recipient_id=recipient_id
    )
    db.add(db_message)
    db.commit()
    db.refresh(db_message)
    
    await manager.send_personal_message(recipient_id, current_user.id, message.content, db)
    
    return db_message
