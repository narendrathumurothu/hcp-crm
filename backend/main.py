from fastapi import FastAPI, Depends, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from database import engine, get_db, Base
from models import Interaction, User
from schemas import (
    InteractionCreate, InteractionUpdate, ChatMessage,
    RegisterRequest, LoginRequest, TokenResponse
)
from agent import run_agent
from auth import hash_password, verify_password, create_access_token, get_current_user
import models

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="HCP CRM API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"message": "HCP CRM API Running!"}

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
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    token = create_access_token({"sub": user.email})
    return TokenResponse(access_token=token, user_name=user.name, user_email=user.email, user_company=user.company_name)

@app.get("/api/auth/me")
def get_me(current_user: User = Depends(get_current_user)):
    return {"id": current_user.id, "name": current_user.name, "email": current_user.email, "company_name": current_user.company_name}

@app.post("/api/interactions")
def create_interaction(data: InteractionCreate, db: Session = Depends(get_db)):
    interaction = Interaction(**data.dict())
    db.add(interaction)
    db.commit()
    db.refresh(interaction)
    return interaction

@app.get("/api/interactions")
def get_interactions(db: Session = Depends(get_db)):
    return db.query(Interaction).order_by(Interaction.created_at.desc()).all()

@app.get("/api/interactions/{id}")
def get_interaction(id: int, db: Session = Depends(get_db)):
    interaction = db.query(Interaction).filter(Interaction.id == id).first()
    if not interaction:
        raise HTTPException(status_code=404, detail="Not found")
    return interaction

@app.put("/api/interactions/{id}")
def update_interaction(id: int, data: InteractionUpdate, db: Session = Depends(get_db)):
    interaction = db.query(Interaction).filter(Interaction.id == id).first()
    if not interaction:
        raise HTTPException(status_code=404, detail="Not found")
    for key, value in data.dict(exclude_unset=True).items():
        setattr(interaction, key, value)
    db.commit()
    db.refresh(interaction)
    return interaction

@app.delete("/api/interactions/{id}")
def delete_interaction(id: int, db: Session = Depends(get_db)):
    interaction = db.query(Interaction).filter(Interaction.id == id).first()
    if not interaction:
        raise HTTPException(status_code=404, detail="Not found")
    db.delete(interaction)
    db.commit()
    return {"message": "Deleted successfully"}

@app.post("/api/chat")
def chat(msg: ChatMessage, db: Session = Depends(get_db)):
    result = run_agent(msg.message)
    if result.get("intent") == "LOG" and result.get("extracted_data"):
        data = result["extracted_data"]
        if data.get("hcp_name"):
            interaction = Interaction(
                hcp_name=data.get("hcp_name"),
                topics=data.get("topics"),
                sentiment=data.get("sentiment", "Neutral"),
                outcomes=data.get("outcomes"),
                follow_up_actions=data.get("follow_up_actions"),
                ai_summary=result.get("response")
            )
            db.add(interaction)
            db.commit()
    return {"response": result.get("response"), "extracted_data": result.get("extracted_data"), "followup_suggestions": result.get("followup_suggestions"), "intent": result.get("intent")}

@app.get("/api/hcp/{hcp_name}")
def get_hcp_profile(hcp_name: str, db: Session = Depends(get_db)):
    interactions = db.query(Interaction).filter(Interaction.hcp_name.ilike(f"%{hcp_name}%")).all()
    return {"hcp_name": hcp_name, "total_interactions": len(interactions), "interactions": interactions}

@app.get("/api/search")
def search_interactions(q: str = Query(...), db: Session = Depends(get_db)):
    results = db.query(Interaction).filter(
        Interaction.hcp_name.ilike(f"%{q}%") | Interaction.topics.ilike(f"%{q}%") |
        Interaction.outcomes.ilike(f"%{q}%") | Interaction.sentiment.ilike(f"%{q}%")
    ).order_by(Interaction.created_at.desc()).all()
    return {"query": q, "total_found": len(results), "results": results}

@app.get("/api/stats")
def get_stats(db: Session = Depends(get_db)):
    interactions = db.query(Interaction).all()
    total = len(interactions)
    if total == 0:
        return {"total_interactions": 0}
    sentiments = {"Positive": 0, "Neutral": 0, "Negative": 0}
    types = {}
    for i in interactions:
        s = i.sentiment or "Neutral"
        sentiments[s] = sentiments.get(s, 0) + 1
        t = i.interaction_type or "Meeting"
        types[t] = types.get(t, 0) + 1
    return {"total_interactions": total, "sentiment_breakdown": sentiments, "interaction_type_breakdown": types, "positive_rate": f"{round(sentiments['Positive'] / total * 100, 1)}%"}

@app.get("/api/interactions/sentiment/{sentiment}")
def get_by_sentiment(sentiment: str, db: Session = Depends(get_db)):
    results = db.query(Interaction).filter(Interaction.sentiment.ilike(sentiment)).order_by(Interaction.created_at.desc()).all()
    return {"sentiment": sentiment, "total": len(results), "interactions": results}

@app.get("/api/followup/{hcp_name}")
def get_followup(hcp_name: str):
    result = run_agent(f"suggest follow up actions for {hcp_name}")
    return {"hcp_name": hcp_name, "suggestions": result.get("followup_suggestions", []), "response": result.get("response")}