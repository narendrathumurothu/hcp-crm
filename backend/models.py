from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean
from sqlalchemy.sql import func
from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, nullable=False, index=True)
    company_name = Column(String(150), nullable=False)
    password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Interaction(Base):
    __tablename__ = "interactions"

    id = Column(Integer, primary_key=True, index=True)
    hcp_name = Column(String(100), nullable=False)
    interaction_type = Column(String(50), default="Meeting")
    date = Column(String(20))
    time = Column(String(10))
    attendees = Column(String(200))
    topics = Column(Text)
    materials_shared = Column(Text)
    samples_distributed = Column(Text)
    sentiment = Column(String(20), default="Neutral")
    outcomes = Column(Text)
    follow_up_actions = Column(Text)
    ai_summary = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Reminder(Base):
    __tablename__ = "reminders"

    id = Column(Integer, primary_key=True, index=True)
    hcp_name = Column(String(100), nullable=False)
    task = Column(String(255), nullable=False)
    reminder_date = Column(String(20))
    reminder_time = Column(String(10))
    status = Column(String(20), default="Pending")
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class SampleInventory(Base):
    __tablename__ = "sample_inventory"

    id = Column(Integer, primary_key=True, index=True)
    hcp_name = Column(String(100), nullable=False)
    medicine_name = Column(String(100), nullable=False)
    quantity = Column(Integer, nullable=False)
    distributed_at = Column(DateTime(timezone=True), server_default=func.now())