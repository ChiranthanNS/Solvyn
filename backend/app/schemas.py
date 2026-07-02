from datetime import datetime
from pydantic import BaseModel

# -------------------------
# USER SCHEMAS
# -------------------------

class UserCreate(BaseModel):
    name: str | None = None
    email: str
    password: str


class UserResponse(BaseModel):
    id: int
    email: str

    class Config:
        from_attributes = True


class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# -------------------------
# DIARY SCHEMAS
# -------------------------

class DiaryCreate(BaseModel):
    content: str


class DiaryResponse(BaseModel):
    id: int
    content: str
    created_at: datetime

    class Config:
        from_attributes = True


# -------------------------
# CONVERSATION MESSAGE SCHEMAS
# -------------------------

class ConversationMessageCreate(BaseModel):
    content: str


class ConversationMessageResponse(BaseModel):
    id: int
    user_id: int
    sender: str
    message: str
    timestamp: datetime

    class Config:
        from_attributes = True


# -------------------------
# AI CHAT REQUEST
# -------------------------

class ChatRequest(BaseModel):
    message: str
