from datetime import datetime
import re

from pydantic import BaseModel, Field, field_validator

# -------------------------
# USER SCHEMAS
# -------------------------

class UserCreate(BaseModel):
    name: str | None = Field(default=None, max_length=80)
    email: str = Field(min_length=6, max_length=254)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        value = value.strip().lower()
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", value):
            raise ValueError("A valid email address is required.")
        return value


class UserResponse(BaseModel):
    id: int
    email: str

    class Config:
        from_attributes = True


class LoginRequest(BaseModel):
    email: str = Field(min_length=6, max_length=254)
    password: str = Field(min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        value = value.strip().lower()
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", value):
            raise ValueError("A valid email address is required.")
        return value


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# -------------------------
# DIARY SCHEMAS
# -------------------------

class DiaryCreate(BaseModel):
    content: str = Field(min_length=1, max_length=6000)

    @field_validator("content")
    @classmethod
    def trim_content(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Diary content cannot be empty.")
        return value


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
    content: str = Field(min_length=1, max_length=8000)

    @field_validator("content")
    @classmethod
    def trim_content(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Message content cannot be empty.")
        return value


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


class SolutionRequest(BaseModel):
    content: str = Field(min_length=3, max_length=6000)

    @field_validator("content")
    @classmethod
    def trim_content(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 3:
            raise ValueError("Describe the problem in at least three characters.")
        return value


class SolutionStep(BaseModel):
    title: str
    description: str


class SolutionNode(BaseModel):
    id: str
    label: str
    parent_id: str | None = None
    description: str = ""


class SolutionResponse(BaseModel):
    title: str
    summary: str
    analysis: list[str] = Field(default_factory=list)
    steps: list[SolutionStep] = Field(default_factory=list)
    tree: list[SolutionNode] = Field(default_factory=list)
    code_language: str | None = None
    code: str | None = None
    formula: str | None = None
    complexity: str = "Medium"
    related_tools: list[str] = Field(default_factory=list)
    elapsed_seconds: float
    token_usage: int | None = None
