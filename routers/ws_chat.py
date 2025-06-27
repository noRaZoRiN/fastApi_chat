from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from fastapi.websockets import WebSocketState
from dependencies import get_current_user
from utils.manager import manager
from database import get_db, SessionLocal
from sqlalchemy.orm import Session
import json
from typing import Dict, Any, Optional, Union

router = APIRouter(prefix="/ws", tags=["WebSocket Chat"])

@router.websocket("/chat")
async def websocket_chat(websocket: WebSocket, token: str):
    db = SessionLocal()
    try:
        user = await get_current_user(token, db)
        
        if isinstance(user, str):
            await websocket.close(code=1008, reason="")
            return
        
        await manager.connect(user.id, websocket)
        
        for group in user.groups:
            manager.add_user_to_group(user.id, group.id)
        
        try:
            while True:
                data = await websocket.receive_text()
                message_data = json.loads(data)
                
                message_type = message_data.get("type", "personal")
                content = message_data.get("content", "")
                
                if message_type == "personal":
                    recipient_id = message_data.get("recipient_id")
                    if recipient_id:
                        await manager.send_personal_message(recipient_id, user.id, content, db)
                
                elif message_type == "group":
                    group_id = message_data.get("group_id")
                    if group_id:
                        await manager.send_group_message(group_id, user.id, content, db)
                
        except WebSocketDisconnect:
            manager.disconnect(user.id)
        except Exception as e:
            manager.disconnect(user.id)
            raise e
    finally:
        db.close()

@router.websocket("/notifications")
async def websocket_notifications(websocket: WebSocket, token: str):
    db = SessionLocal()
    try:
        user = await get_current_user(token, db)
        
        if isinstance(user, str):
            await websocket.close(code=1008, reason="")
            return
        
        await websocket.accept()
        
        unread_count = db.query(db.func.count()).filter_by(user_id=user.id, is_read=False).scalar()
        await websocket.send_text(json.dumps({
            "type": "unread_count",
            "count": unread_count
        }))
        
        try:
            while True:
                await websocket.receive_text()
        except WebSocketDisconnect:
            pass
    finally:
        db.close()
