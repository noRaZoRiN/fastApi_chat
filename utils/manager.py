from fastapi import WebSocket, Depends
from typing import Dict, List, Set, Union
from sqlalchemy.orm import Session
import json
from datetime import datetime

from models import MessageDB, NotificationDB, UserDB, GroupDB
from database import get_db

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[int, WebSocket] = {}
        self.user_groups: Dict[int, Set[int]] = {}

    async def connect(self, user_id: int, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[user_id] = websocket
        self.user_groups[user_id] = set()

    def disconnect(self, user_id: int):
        if user_id in self.active_connections:
            del self.active_connections[user_id]
        if user_id in self.user_groups:
            del self.user_groups[user_id]

    def add_user_to_group(self, user_id: int, group_id: int):
        if user_id in self.user_groups:
            self.user_groups[user_id].add(group_id)

    def remove_user_from_group(self, user_id: int, group_id: int):
        if user_id in self.user_groups and group_id in self.user_groups[user_id]:
            self.user_groups[user_id].remove(group_id)

    async def send_personal_message(self, recipient_id: int, sender_id: int, message: str, db: Session):
        db_message = MessageDB(
            content=message,
            sender_id=sender_id,
            recipient_id=recipient_id,
            timestamp=datetime.utcnow()
        )
        db.add(db_message)
        
        notification = NotificationDB(
            user_id=recipient_id,
            content=f"New message from user {sender_id}",
            timestamp=datetime.utcnow()
        )
        db.add(notification)
        db.commit()
        
        if recipient_id in self.active_connections:
            sender = db.query(UserDB).filter(UserDB.id == sender_id).first()
            sender_name = sender.username if sender else f"User {sender_id}"
            message_data = {
                "type": "personal_message",
                "sender_id": sender_id,
                "sender_name": sender_name,
                "content": message,
                "timestamp": datetime.utcnow().isoformat()
            }
            await self.active_connections[recipient_id].send_text(json.dumps(message_data))

    async def send_group_message(self, group_id: int, sender_id: int, message: str, db: Session):
        group = db.query(GroupDB).filter(GroupDB.id == group_id).first()
        if not group:
            return
        
        db_message = MessageDB(
            content=message,
            sender_id=sender_id,
            group_id=group_id,
            timestamp=datetime.utcnow()
        )
        db.add(db_message)
        db.commit()
        
        sender = db.query(UserDB).filter(UserDB.id == sender_id).first()
        sender_name = sender.username if sender else f"User {sender_id}"
        
        message_data = {
            "type": "group_message",
            "group_id": group_id,
            "group_name": group.name,
            "sender_id": sender_id,
            "sender_name": sender_name,
            "content": message,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        for member in group.members:
            if member.id != sender_id and member.id in self.active_connections:
                await self.active_connections[member.id].send_text(json.dumps(message_data))
                
                notification = NotificationDB(
                    user_id=member.id,
                    content=f"New message in group {group.name} from {sender_name}",
                    timestamp=datetime.utcnow()
                )
                db.add(notification)
        
        db.commit()

    async def send_notification(self, user_id: int, content: str, db: Session):
        notification = NotificationDB(
            user_id=user_id,
            content=content,
            timestamp=datetime.utcnow()
        )
        db.add(notification)
        db.commit()
        
        if user_id in self.active_connections:
            notification_data = {
                "type": "notification",
                "content": content,
                "timestamp": datetime.utcnow().isoformat()
            }
            await self.active_connections[user_id].send_text(json.dumps(notification_data))

manager = ConnectionManager()
