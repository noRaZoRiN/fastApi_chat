from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Table, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

# SQLAlchemy 
group_members = Table(
    "group_members",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id")),
    Column("group_id", Integer, ForeignKey("groups.id"))
)

class UserDB(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password = Column(String)
    email = Column(String, unique=True, index=True)
    messages_sent = relationship("MessageDB", back_populates="sender", foreign_keys="MessageDB.sender_id")
    groups = relationship("GroupDB", secondary=group_members, back_populates="members")
    notifications = relationship("NotificationDB", back_populates="user")

class GroupDB(Base):
    __tablename__ = "groups"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    members = relationship("UserDB", secondary=group_members, back_populates="groups")
    messages = relationship("MessageDB", back_populates="group")

class MessageDB(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True, index=True)
    content = Column(String)
    sender_id = Column(Integer, ForeignKey("users.id"))
    group_id = Column(Integer, ForeignKey("groups.id"), nullable=True)
    recipient_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    sender = relationship("UserDB", back_populates="messages_sent", foreign_keys=[sender_id])
    group = relationship("GroupDB", back_populates="messages", foreign_keys=[group_id])

class NotificationDB(Base):
    __tablename__ = "notifications"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    content = Column(String)
    is_read = Column(Boolean, default=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    user = relationship("UserDB", back_populates="notifications")

# Pydantic 
class User(BaseModel):
    username: str
    password: str
    email: Optional[str] = None

class UserCreate(User):
    pass

class UserResponse(BaseModel):
    id: int
    username: str
    email: Optional[str] = None

    class Config:
        orm_mode = True

class Token(BaseModel):
    access_token: str
    token_type: str

class Message(BaseModel):
    content: str
    recispient_id: Optional[int] = None
    group_id: Optional[int] = None

class MessageResponse(BaseModel):
    id: int
    content: str
    sender_id: int
    recipient_id: Optional[int] = None
    group_id: Optional[int] = None
    timestamp: datetime

    class Config:
        orm_mode = True

class Group(BaseModel):
    name: str
    member_ids: List[int]

class GroupResponse(BaseModel):
    id: int
    name: str
    members: List[UserResponse]
    created_at: datetime

    class Config:
        orm_mode = True

class Notification(BaseModel):
    user_id: int
    content: str
    is_read: bool = False

class NotificationResponse(BaseModel):
    id: int
    content: str
    is_read: bool
    timestamp: datetime

    class Config:
        orm_mode = True

# Фейковая БД пользователей 
fake_users_db = {
    "user1": {"username": "", "password": ""},
    "user2": {"username": "", "password": ""},
}
