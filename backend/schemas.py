from pydantic import BaseModel, EmailStr
from typing import Optional


# ─────────────────────────────────────────
# Auth Schemas
# ─────────────────────────────────────────
class RegisterRequest(BaseModel):
    name: str
    email: EmailStr
    company_name: str
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_name: str
    user_email: str
    user_company: str


# ─────────────────────────────────────────
# Interaction Schemas
# ─────────────────────────────────────────
class InteractionCreate(BaseModel):
    hcp_name: str
    interaction_type: Optional[str] = "Meeting"
    date: Optional[str] = None
    time: Optional[str] = None
    attendees: Optional[str] = None
    topics: Optional[str] = None
    materials_shared: Optional[str] = None
    samples_distributed: Optional[str] = None
    sentiment: Optional[str] = "Neutral"
    outcomes: Optional[str] = None
    follow_up_actions: Optional[str] = None


class InteractionUpdate(BaseModel):
    hcp_name: Optional[str] = None
    interaction_type: Optional[str] = None
    date: Optional[str] = None
    time: Optional[str] = None
    attendees: Optional[str] = None
    topics: Optional[str] = None
    materials_shared: Optional[str] = None
    samples_distributed: Optional[str] = None
    sentiment: Optional[str] = None
    outcomes: Optional[str] = None
    follow_up_actions: Optional[str] = None
# ─────────────────────────────────────────
# Chat Schema
# ─────────────────────────────────────────
class ChatMessage(BaseModel):
    message: str