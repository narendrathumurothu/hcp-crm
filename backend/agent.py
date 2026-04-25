import operator
import json
import os
import sqlite3
from typing import TypedDict, Annotated, Optional
from dotenv import load_dotenv

from langchain_groq import ChatGroq
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode

from langgraph.checkpoint.sqlite import SqliteSaver

# Import your database session and models
from database import SessionLocal
from models import Interaction, Reminder, SampleInventory

load_dotenv()

llm = ChatGroq(
    model="gemma2-9b-it",
    api_key=os.getenv("GROQ_API_KEY", ""),
    temperature=0.1
)

# ──────────────────────────────────────────────────────────
# CRM TOOLS DEFINITION
# ──────────────────────────────────────────────────────────

@tool
def log_interaction(
    hcp_name: str, 
    interaction_type: str = "Meeting",
    date: Optional[str] = None,
    time: Optional[str] = None,
    attendees: Optional[str] = None,
    topics: Optional[str] = None,
    materials_shared: Optional[str] = None,
    samples_distributed: Optional[str] = None,
    sentiment: str = "Neutral",
    outcomes: Optional[str] = None,
    follow_up_actions: Optional[str] = None
) -> str:
    """Extract and log a new HCP interaction."""
    try:
        with SessionLocal() as db:
            interaction = Interaction(
                hcp_name=hcp_name,
                interaction_type=interaction_type,
                date=date,
                time=time,
                attendees=attendees,
                topics=topics,
                materials_shared=materials_shared,
                samples_distributed=samples_distributed,
                sentiment=sentiment,
                outcomes=outcomes,
                follow_up_actions=follow_up_actions
            )
            db.add(interaction)
            db.commit()
            db.refresh(interaction)
            return json.dumps({
                "status": "success", 
                "id": interaction.id, 
                "hcp": interaction.hcp_name,
                "extracted_data": {
                    "hcp_name": interaction.hcp_name,
                    "topics": interaction.topics,
                    "sentiment": interaction.sentiment,
                    "outcomes": interaction.outcomes,
                    "follow_up_actions": interaction.follow_up_actions
                }
            })
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})

@tool
def edit_interaction(hcp_name_or_id: str, field_to_update: str, new_value: str) -> str:
    """Update a specific field of an existing interaction."""
    try:
        with SessionLocal() as db:
            try:
                i_id = int(str(hcp_name_or_id).strip())
                record = db.query(Interaction).filter(Interaction.id == i_id).first()
            except ValueError:
                record = db.query(Interaction).filter(Interaction.hcp_name.ilike(f"%{hcp_name_or_id}%")).order_by(Interaction.created_at.desc()).first()

            if not record:
                return json.dumps({"status": "error", "message": "Interaction not found."})

            setattr(record, field_to_update.lower().strip(), new_value)
            db.commit()
            return json.dumps({"status": "success", "message": f"Updated {field_to_update} for {record.hcp_name}"})
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})

@tool
def add_reminder(hcp_name: str, task: str, date: str, time: str) -> str:
    """Set a reminder for a future task."""
    try:
        with SessionLocal() as db:
            new_rem = Reminder(hcp_name=hcp_name, task=task, reminder_date=date, reminder_time=time)
            db.add(new_rem)
            db.commit()
            return json.dumps({"status": "success", "message": f"Reminder set for {hcp_name}"})
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})

@tool
def track_sample(hcp_name: str, medicine_name: str, quantity: int) -> str:
    """Track medical samples distributed."""
    try:
        with SessionLocal() as db:
            sample = SampleInventory(hcp_name=hcp_name, medicine_name=medicine_name, quantity=quantity)
            db.add(sample)
            db.commit()
            return json.dumps({"status": "success", "message": f"Logged {medicine_name} for {hcp_name}"})
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})

@tool
def get_hcp_profile(hcp_name: str) -> str:
    """Get history and analytics of a specific doctor."""
    try:
        with SessionLocal() as db:
            records = db.query(Interaction).filter(Interaction.hcp_name.ilike(f"%{hcp_name}%")).all()
            if not records: return json.dumps({"status": "not_found"})
            return json.dumps({"hcp": hcp_name, "total_visits": len(records)})
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})

# ──────────────────────────────────────────────────────────
# LANGGRAPH CONFIGURATION
# ──────────────────────────────────────────────────────────

class AgentState(TypedDict):
    messages: Annotated[list, operator.add]

tools = [log_interaction, edit_interaction, add_reminder, track_sample, get_hcp_profile]
tool_node = ToolNode(tools)
llm_with_tools = llm.bind_tools(tools)

SYSTEM_PROMPT = """You are a Pharmaceutical CRM Assistant. 
1. DO NOT guess update values. Ask if missing.
2. Respond in the same language the user uses (Telugu, Hindi, or English).
3. Use thread history to remember the current doctor."""

def agent_node(state: AgentState):
    messages = [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]
    return {"messages": [llm_with_tools.invoke(messages)]}

def should_continue(state: AgentState):
    last = state["messages"][-1]
    return "tools" if hasattr(last, "tool_calls") and last.tool_calls else END

# Database connection for checkpoints
conn = sqlite3.connect("checkpoints.db", check_same_thread=False)
memory = SqliteSaver(conn)

workflow = StateGraph(AgentState)
workflow.add_node("agent", agent_node)
workflow.add_node("tools", tool_node)
workflow.set_entry_point("agent")
workflow.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
workflow.add_edge("tools", "agent")

app_graph = workflow.compile(checkpointer=memory)

def run_agent(message: str, thread_id: str = "default_session"):
    config = {"configurable": {"thread_id": thread_id}}
    try:
        result = app_graph.invoke({"messages": [HumanMessage(content=message)]}, config)
        
        response_data = {"response": result["messages"][-1].content}
        
        # Check if the AI used the log_interaction tool and return the extracted data to frontend
        for msg in reversed(result["messages"]):
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                for tc in msg.tool_calls:
                    if tc["name"] == "log_interaction":
                        response_data["extracted_data"] = tc["args"]
                        break
        
        return response_data
    except Exception as e:
        return {"response": f"Error: {str(e)}"}