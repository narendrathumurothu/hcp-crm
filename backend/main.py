from fastapi import FastAPI, Depends, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from database import engine, get_db, Base
from models import Interaction, User, Reminder, SampleInventory # Added new models
from schemas import (
    InteractionCreate, InteractionUpdate, ChatMessage,
    RegisterRequest, LoginRequest, TokenResponse
)
from agent import run_agent
from auth import hash_password, verify_password, create_access_token, get_current_user
import models

# Automatically create tables in DB
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="HCP CRM API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── AUTHENTICATION ENDPOINTS ───

@app.post("/api/auth/register", response_model=TokenResponse)
def register(data: RegisterRequest, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == data.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    user = User(
        name=data.name,
        email=data.email,
        company_name=data.company_name,
        password=hash_password(data.password)
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_access_token({"sub": user.email})
    return TokenResponse(access_token=token, user_name=user.name, user_email=user.email, user_company=user.company_name)

@app.post("/api/auth/login", response_model=TokenResponse)
def login(data: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email).first()
    if not user or not verify_password(data.password, user.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    token = create_access_token({"sub": user.email})
    return TokenResponse(access_token=token, user_name=user.name, user_email=user.email, user_company=user.company_name)

# ─── CHAT AGENT ENDPOINT (CLEANED) ───

@app.post("/api/chat")
def chat(msg: ChatMessage, current_user: User = Depends(get_current_user)):
    """
    The Agent handles DB logging, editing, and reminders internally.
    We pass current_user.email as thread_id for personal memory.
    """
    # Simply run the agent. The agent's tools handle the DB work now.
    result = run_agent(msg.message, thread_id=str(current_user.id))
    return result

# ─── REMINDERS & SAMPLES ENDPOINTS ───

@app.get("/api/reminders")
def get_reminders(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Fetch all pending reminders."""
    return db.query(Reminder).order_by(Reminder.reminder_date.asc()).all()

@app.get("/api/samples")
def get_samples(db: Session = Depends(get_db)):
    """Fetch all sample distribution records."""
    return db.query(SampleInventory).all()

# ─── EXISTING CRUD (Kept for Frontend Tables) ───

@app.get("/api/interactions")
def get_interactions(db: Session = Depends(get_db)):
    return db.query(Interaction).order_by(Interaction.created_at.desc()).all()

@app.get("/api/stats")
def get_stats(db: Session = Depends(get_db)):
    interactions = db.query(Interaction).all()
    total = len(interactions)
    if total == 0: return {"total_interactions": 0}
    
    sentiments = {"Positive": 0, "Neutral": 0, "Negative": 0}
    for i in interactions:
        s = i.sentiment or "Neutral"
        sentiments[s] = sentiments.get(s, 0) + 1
    
    return {
        "total_interactions": total, 
        "sentiment_breakdown": sentiments,
        "positive_rate": f"{round(sentiments['Positive'] / total * 100, 1)}%" if total > 0 else "0%"
    }

@app.get("/")
def root():
    return {"message": "HCP CRM API is live!"}