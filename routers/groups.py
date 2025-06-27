from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session
from typing import List

from models import Group, GroupResponse, UserDB, GroupDB, MessageResponse, MessageDB, Message
from dependencies import get_current_user
from database import get_db
from utils.manager import manager

router = APIRouter(prefix="/groups", tags=["Groups"])

@router.post("", response_model=GroupResponse)
async def create_group(group: Group, current_user: UserDB = Depends(get_current_user), db: Session = Depends(get_db)):
    if isinstance(current_user, str):
        raise HTTPException(status_code=400, detail="")
    
    db_group = GroupDB(name=group.name)
    db.add(db_group)
    db.commit()
    db.refresh(db_group)
    
    db_group.members.append(current_user)
    
    for member_id in group.member_ids:
        member = db.query(UserDB).filter(UserDB.id == member_id).first()
        if member:
            db_group.members.append(member)
    
    db.commit()
    db.refresh(db_group)
    
    for member in db_group.members:
        if member.id in manager.active_connections:
            manager.add_user_to_group(member.id, db_group.id)
    
    return db_group

@router.get("", response_model=List[GroupResponse])
async def get_user_groups(current_user: UserDB = Depends(get_current_user), db: Session = Depends(get_db)):
    if isinstance(current_user, str):
        raise HTTPException(status_code=400, detail="")
    
    return current_user.groups

@router.get("/{group_id}", response_model=GroupResponse)
async def get_group(group_id: int, current_user: UserDB = Depends(get_current_user), db: Session = Depends(get_db)):
    if isinstance(current_user, str):
        raise HTTPException(status_code=400, detail="")
    
    group = db.query(GroupDB).filter(GroupDB.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    
    if current_user not in group.members:
        raise HTTPException(status_code=403, detail="Not a member of this group")
    
    return group

@router.post("/{group_id}/members/{user_id}")
async def add_member_to_group(
    group_id: int, 
    user_id: int, 
    current_user: UserDB = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    if isinstance(current_user, str):
        raise HTTPException(status_code=400, detail="")
    
    group = db.query(GroupDB).filter(GroupDB.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    
    if current_user not in group.members:
        raise HTTPException(status_code=403, detail="Not a member of this group")
    
    user_to_add = db.query(UserDB).filter(UserDB.id == user_id).first()
    if not user_to_add:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user_to_add in group.members:
        raise HTTPException(status_code=400, detail="User is already a member of this group")
    
    group.members.append(user_to_add)
    db.commit()
    
    if user_id in manager.active_connections:
        manager.add_user_to_group(user_id, group_id)
    
    await manager.send_notification(
        user_id=user_id,
        content=f"You were added to group {group.name}",
        db=db
    )
    
    return {"status": "success"}

@router.delete("/{group_id}/members/{user_id}")
async def remove_member_from_group(
    group_id: int, 
    user_id: int, 
    current_user: UserDB = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    if isinstance(current_user, str):
        raise HTTPException(status_code=400, detail="")
    
    group = db.query(GroupDB).filter(GroupDB.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    
    if current_user not in group.members:
        raise HTTPException(status_code=403, detail="Not a member of this group")
    
    user_to_remove = db.query(UserDB).filter(UserDB.id == user_id).first()
    if not user_to_remove:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user_to_remove not in group.members:
        raise HTTPException(status_code=400, detail="User is not a member of this group")
    
    group.members.remove(user_to_remove)
    db.commit()
    
    if user_id in manager.active_connections:
        manager.remove_user_from_group(user_id, group_id)
    
    await manager.send_notification(
        user_id=user_id,
        content=f"You were removed from group {group.name}",
        db=db
    )
    
    return {"status": "success"}

@router.get("/{group_id}/messages", response_model=List[MessageResponse])
async def get_group_messages(
    group_id: int, 
    current_user: UserDB = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    if isinstance(current_user, str):
        raise HTTPException(status_code=400, detail="")
    
    group = db.query(GroupDB).filter(GroupDB.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    
    if current_user not in group.members:
        raise HTTPException(status_code=403, detail="Not a member of this group")
    
    messages = db.query(MessageDB).filter(MessageDB.group_id == group_id).order_by(MessageDB.timestamp).all()
    return messages

@router.post("/{group_id}/messages", response_model=MessageResponse)
async def send_group_message(
    group_id: int,
    message: Message,
    current_user: UserDB = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if isinstance(current_user, str):
        raise HTTPException(status_code=400, detail="")
    
    group = db.query(GroupDB).filter(GroupDB.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    
    if current_user not in group.members:
        raise HTTPException(status_code=403, detail="Not a member of this group")
    
    db_message = MessageDB(
        content=message.content,
        sender_id=current_user.id,
        group_id=group_id
    )
    db.add(db_message)
    db.commit()
    db.refresh(db_message)
    
    await manager.send_group_message(group_id, current_user.id, message.content, db)
    
    return db_message
