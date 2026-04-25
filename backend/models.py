import operator
import json
import os
from typing import TypedDict, Annotated
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

# Initialize LLM with Groq
llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    api_key=os.getenv("GROQ_API_KEY"),
    temperature=0.1
)

# ──────────────────────────────────────────────────────────
# CRM TOOLS DEFINITION
# ──────────────────────────────────────────────────────────

@tool
def log_interaction(text: str) -> str:
    """Extract and log a new HCP interaction from natural language."""
    extraction_prompt = f"Extract interaction details from: {text}. Return ONLY valid JSON."
    try:
        response = llm.invoke([HumanMessage(content=extraction_prompt)])
        data = json.loads(response.content.strip().replace("```json", "").replace("```", ""))
        
        with SessionLocal() as db:
            interaction = Interaction(**data) # Matches fields in your Interaction model
            db.add(interaction)
            db.commit()
            db.refresh(interaction)
            return json.dumps({"status": "success", "id": interaction.id, "hcp": interaction.hcp_name})
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})

@tool
def edit_interaction(hcp_name_or_id: str, field_to_update: str, new_value: str) -> str:
    """Update a specific field of an existing interaction. Requires field and value."""
    try:
        with SessionLocal() as db:
            # Search by ID first, then by Name
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
    """Set a reminder for a future task (e.g., 'Call Dr. Raju next week')."""
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
    """Track medical samples distributed to an HCP."""
    try:
        with SessionLocal() as db:
            sample = SampleInventory(hcp_name=hcp_name, medicine_name=medicine_name, quantity=quantity)
            db.add(sample)
            db.commit()
            return json.dumps({"status": "success", "message": f"Logged {quantity} units of {medicine_name}"})
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

# Add other tools (search_interactions, get_interaction_stats, suggest_followup, analyze_sentiment)
# using similar logic as above...

# ──────────────────────────────────────────────────────────
# LANGGRAPH CONFIGURATION
# ──────────────────────────────────────────────────────────

class AgentState(TypedDict):
    messages: Annotated[list, operator.add]

# Tool list for the agent
tools = [log_interaction, edit_interaction, add_reminder, track_sample, 
         get_hcp_profile] # Add others to this list

tool_node = ToolNode(tools)
llm_with_tools = llm.bind_tools(tools)

# Strict system prompt to prevent hallucinations
SYSTEM_PROMPT = """You are a Pharmaceutical CRM Assistant. 

STRICT RULES:
1. DO NOT assume update values. If a user says "Edit Dr. Raju", ask "What field should I update and what is the new value?"
2. If the user speaks Telugu, you MUST respond in Telugu.
3. Use previous conversation history to understand context (e.g., if Dr. Raju was just mentioned, 'he' refers to Dr. Raju).
4. For reminders and samples, extract date/time/quantity precisely."""

def agent_node(state: AgentState):
    # Process messages with System Prompt
    messages = [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]
    return {"messages": [llm_with_tools.invoke(messages)]}

def should_continue(state: AgentState):
    # Router logic to check for tool calls
    last = state["messages"][-1]
    return "tools" if hasattr(last, "tool_calls") and last.tool_calls else END

# Memory Persistence Setup
memory = SqliteSaver.from_conn_string(":memory:")

workflow = StateGraph(AgentState)
workflow.add_node("agent", agent_node)
workflow.add_node("tools", tool_node)
workflow.set_entry_point("agent")
workflow.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
workflow.add_edge("tools", "agent")

app_graph = workflow.compile(checkpointer=memory)

# ──────────────────────────────────────────────────────────
# FINAL EXECUTION FUNCTION
# ──────────────────────────────────────────────────────────

def run_agent(message: str, thread_id: str = "default_session"):
    """Run the agent with memory persistence using thread_id."""
    config = {"configurable": {"thread_id": thread_id}}
    try:
        result = app_graph.invoke({"messages": [HumanMessage(content=message)]}, config)
        return {"response": result["messages"][-1].content}
    except Exception as e:
        return {"response": f"Error: {str(e)}"}