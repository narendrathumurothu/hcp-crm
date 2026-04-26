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
    model="llama-3.3-70b-versatile",
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
def delete_interaction(hcp_name_or_id: str) -> str:
    """Delete an existing interaction record."""
    try:
        with SessionLocal() as db:
            try:
                i_id = int(str(hcp_name_or_id).strip())
                record = db.query(Interaction).filter(Interaction.id == i_id).first()
            except ValueError:
                record = db.query(Interaction).filter(Interaction.hcp_name.ilike(f"%{hcp_name_or_id}%")).order_by(Interaction.created_at.desc()).first()

            if not record:
                return json.dumps({"status": "error", "message": "Interaction not found."})

            db.delete(record)
            db.commit()
            return json.dumps({"status": "success", "message": f"Deleted interaction for {record.hcp_name}"})
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})

@tool
def add_reminder(hcp_name: str, task: str, date: Optional[str] = None, time: Optional[str] = None) -> str:
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
def track_sample(hcp_name: str, medicine_name: str, quantity: Optional[int] = 1) -> str:
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

tools = [log_interaction, edit_interaction, delete_interaction, add_reminder, track_sample, get_hcp_profile]
tool_node = ToolNode(tools)
llm_with_tools = llm.bind_tools(tools)

SYSTEM_PROMPT = """You are an expert Pharmaceutical CRM Assistant. Your goal is to help medical sales representatives log their field activities accurately and efficiently.
1. Use the provided tools ONLY when the user's input explicitly indicates an action like logging, editing, deleting, tracking samples, or setting reminders.
2. If the user just says a greeting like "hi", "hello", or asks a general question, DO NOT use any tools. Just reply politely and ask how you can help them today.
3. If the user mentions an interaction, USE the `log_interaction` tool. Extract the HCP name, topics, sentiment, outcomes, and follow up actions.
4. If the user asks to edit or change a record, USE the `edit_interaction` tool.
5. If the user asks to delete or remove a record, USE the `delete_interaction` tool.
6. If the user mentions giving a sample, USE the `track_sample` tool.
7. If the user mentions a follow-up or scheduling something in the future, USE the `add_reminder` tool.
8. DO NOT ask the user for missing information if they are logging data. If a parameter is not explicitly provided by the user, leave it empty or use a reasonable default.
9. Respond in the same language the user uses (Telugu, Hindi, or English).
10. Use thread history to remember the current doctor."""

def agent_node(state: AgentState):
    messages = state["messages"]
    
    # Trim history to the last 2 HumanMessages to avoid token limit errors (TPM limits)
    human_indices = [i for i, msg in enumerate(messages) if isinstance(msg, HumanMessage)]
    if len(human_indices) > 2:
        trimmed_messages = messages[human_indices[-2]:]
    else:
        trimmed_messages = messages
        
    final_messages = [SystemMessage(content=SYSTEM_PROMPT)] + trimmed_messages
    return {"messages": [llm_with_tools.invoke(final_messages)]}

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