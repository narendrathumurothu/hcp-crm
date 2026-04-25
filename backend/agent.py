from langchain_groq import ChatGroq
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from typing import TypedDict, Annotated
import operator
import json
import os
from dotenv import load_dotenv
from database import SessionLocal
from models import Interaction

load_dotenv()

llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    api_key=os.getenv("GROQ_API_KEY"),
    temperature=0.3
)

# ─────────────────────────────────────────
# TOOL 1: Log Interaction
# ─────────────────────────────────────────
@tool
def log_interaction(text: str) -> str:
    """
    Extracts structured interaction data from natural language text using LLM
    and saves it to the database. Use this when user wants to log/record a new HCP interaction.
    """
    extraction_prompt = f"""
    Extract the following fields from this interaction description.
    Return ONLY a valid JSON object with these exact keys:
    - hcp_name (string)
    - interaction_type (string: Meeting/Call/Email/Visit)
    - topics (string)
    - sentiment (string: Positive/Neutral/Negative)
    - outcomes (string)
    - follow_up_actions (string)
    - ai_summary (string: 2-3 sentence summary)

    Text: {text}

    Return only the JSON, no extra text, no markdown.
    """
    try:
        response = llm.invoke([HumanMessage(content=extraction_prompt)])
        raw = response.content.strip()
        if "```" in raw:
            raw = raw.split("```")[1].replace("json", "").strip()
        data = json.loads(raw)

        db = SessionLocal()
        interaction = Interaction(
            hcp_name=data.get("hcp_name", "Unknown"),
            interaction_type=data.get("interaction_type", "Meeting"),
            topics=data.get("topics", ""),
            sentiment=data.get("sentiment", "Neutral"),
            outcomes=data.get("outcomes", ""),
            follow_up_actions=data.get("follow_up_actions", ""),
            ai_summary=data.get("ai_summary", "")
        )
        db.add(interaction)
        db.commit()
        db.refresh(interaction)
        interaction_id = interaction.id
        db.close()

        return json.dumps({
            "status": "success",
            "message": f"Interaction with {data.get('hcp_name')} logged successfully! ID: {interaction_id}",
            "interaction_id": interaction_id,
            "data": data
        })
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})


# ─────────────────────────────────────────
# TOOL 2: Edit Interaction
# ─────────────────────────────────────────
@tool
def edit_interaction(interaction_id: str, updates: str) -> str:
    """
    Edits/updates an existing interaction in the database by its ID.
    interaction_id must be a string of digits like "1" or "2".
    updates should be a JSON string with fields to update.
    Use this when user wants to modify or correct a logged interaction.
    """
    try:
        # Strip and clean interaction_id to ensure it's a valid integer
        clean_id = str(interaction_id).strip().replace('"', '').replace("'", "")
        interaction_id_int = int(clean_id)

        # Parse updates JSON string
        if isinstance(updates, str):
            updates_clean = updates.strip()
            if "```" in updates_clean:
                updates_clean = updates_clean.split("```")[1].replace("json", "").strip()
            update_data = json.loads(updates_clean)
        else:
            update_data = updates

        db = SessionLocal()
        interaction = db.query(Interaction).filter(
            Interaction.id == interaction_id_int
        ).first()

        if not interaction:
            db.close()
            return json.dumps({
                "status": "error",
                "message": f"Interaction ID {interaction_id_int} not found. Use search_interactions to find the correct ID."
            })

        allowed_fields = [
            "hcp_name", "interaction_type", "date", "time",
            "attendees", "topics", "materials_shared",
            "samples_distributed", "sentiment", "outcomes",
            "follow_up_actions", "ai_summary"
        ]

        updated = []
        for key, value in update_data.items():
            if key in allowed_fields and hasattr(interaction, key):
                setattr(interaction, key, value)
                updated.append(key)

        db.commit()
        db.refresh(interaction)
        db.close()

        return json.dumps({
            "status": "success",
            "message": f"Interaction ID {interaction_id_int} updated successfully.",
            "updated_fields": updated
        })
    except ValueError:
        return json.dumps({
            "status": "error",
            "message": f"Invalid interaction ID '{interaction_id}'. Must be a number like 1 or 2."
        })
    except json.JSONDecodeError as e:
        return json.dumps({
            "status": "error",
            "message": f"Invalid updates format. Must be valid JSON. Error: {str(e)}"
        })
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})


# ─────────────────────────────────────────
# TOOL 3: Get HCP Profile
# ─────────────────────────────────────────
@tool
def get_hcp_profile(hcp_name: str) -> str:
    """
    Retrieves full profile and interaction history of a Healthcare Professional (HCP/Doctor)
    by their name. Use this when user asks about a specific doctor or HCP.
    """
    try:
        db = SessionLocal()
        interactions = db.query(Interaction).filter(
            Interaction.hcp_name.ilike(f"%{hcp_name}%")
        ).order_by(Interaction.created_at.desc()).all()
        db.close()

        if not interactions:
            return json.dumps({
                "status": "not_found",
                "message": f"No interactions found for {hcp_name}"
            })

        sentiments = [i.sentiment for i in interactions if i.sentiment]
        positive = sentiments.count("Positive")
        negative = sentiments.count("Negative")
        neutral = sentiments.count("Neutral")

        history = [{
            "id": i.id,
            "date": i.date,
            "type": i.interaction_type,
            "topics": i.topics,
            "sentiment": i.sentiment,
            "outcomes": i.outcomes
        } for i in interactions]

        return json.dumps({
            "status": "success",
            "hcp_name": hcp_name,
            "total_interactions": len(interactions),
            "sentiment_summary": {
                "Positive": positive,
                "Neutral": neutral,
                "Negative": negative
            },
            "recent_interactions": history[:5]
        })
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})


# ─────────────────────────────────────────
# TOOL 4: Analyze Sentiment
# ─────────────────────────────────────────
@tool
def analyze_sentiment(text: str) -> str:
    """
    Analyzes the sentiment of an HCP interaction description or conversation.
    Returns Positive, Neutral, or Negative with reasoning.
    Use this when user wants to understand the tone or sentiment of a meeting.
    """
    prompt = f"""
    Analyze the sentiment of this HCP interaction.
    Return ONLY a JSON object with:
    - sentiment: "Positive", "Neutral", or "Negative"
    - confidence: "High", "Medium", or "Low"
    - reasoning: one sentence explanation
    - key_signals: list of 2-3 words/phrases that indicate the sentiment

    Text: {text}

    Return only the JSON, no extra text, no markdown.
    """
    try:
        response = llm.invoke([HumanMessage(content=prompt)])
        raw = response.content.strip()
        if "```" in raw:
            raw = raw.split("```")[1].replace("json", "").strip()
        data = json.loads(raw)
        return json.dumps({"status": "success", "analysis": data})
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})


# ─────────────────────────────────────────
# TOOL 5: Suggest Follow-up
# ─────────────────────────────────────────
@tool
def suggest_followup(hcp_name: str) -> str:
    """
    Suggests AI-powered follow-up actions based on the HCP's recent interaction history.
    Use this when user asks what to do next with a doctor or HCP.
    """
    try:
        db = SessionLocal()
        interactions = db.query(Interaction).filter(
            Interaction.hcp_name.ilike(f"%{hcp_name}%")
        ).order_by(Interaction.created_at.desc()).limit(3).all()
        db.close()

        if not interactions:
            return json.dumps({
                "status": "not_found",
                "message": f"No history found for {hcp_name}"
            })

        history_text = "\n".join([
            f"- {i.interaction_type} on {i.date}: Topics: {i.topics}, Outcomes: {i.outcomes}, Sentiment: {i.sentiment}"
            for i in interactions
        ])

        prompt = f"""
        Based on these recent interactions with {hcp_name}:
        {history_text}

        Suggest 3 specific follow-up actions for a pharma field representative.
        Return ONLY a JSON object with:
        - suggestions: list of 3 action strings
        - priority: "High", "Medium", or "Low"
        - best_time_to_contact: suggestion string

        Return only the JSON, no extra text, no markdown.
        """
        response = llm.invoke([HumanMessage(content=prompt)])
        raw = response.content.strip()
        if "```" in raw:
            raw = raw.split("```")[1].replace("json", "").strip()
        data = json.loads(raw)

        return json.dumps({
            "status": "success",
            "hcp_name": hcp_name,
            "followup": data
        })
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})


# ─────────────────────────────────────────
# TOOL 6: Search Interactions
# ─────────────────────────────────────────
@tool
def search_interactions(query: str) -> str:
    """
    Searches interactions by HCP name, topics, outcomes, or sentiment keyword.
    Use this when user wants to find specific interactions or filter by criteria.
    """
    try:
        db = SessionLocal()
        results = db.query(Interaction).filter(
            Interaction.hcp_name.ilike(f"%{query}%") |
            Interaction.topics.ilike(f"%{query}%") |
            Interaction.outcomes.ilike(f"%{query}%") |
            Interaction.sentiment.ilike(f"%{query}%") |
            Interaction.interaction_type.ilike(f"%{query}%")
        ).order_by(Interaction.created_at.desc()).limit(10).all()
        db.close()

        if not results:
            return json.dumps({
                "status": "not_found",
                "message": f"No interactions found matching '{query}'"
            })

        data = [{
            "id": i.id,
            "hcp_name": i.hcp_name,
            "date": i.date,
            "type": i.interaction_type,
            "topics": i.topics,
            "sentiment": i.sentiment,
            "outcomes": i.outcomes
        } for i in results]

        return json.dumps({
            "status": "success",
            "query": query,
            "total_found": len(data),
            "results": data
        })
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})


# ─────────────────────────────────────────
# TOOL 7: Get Interaction Stats
# ─────────────────────────────────────────
@tool
def get_interaction_stats(hcp_name: str = "") -> str:
    """
    Returns analytics and statistics about interactions.
    If hcp_name is provided, returns stats for that HCP only.
    Use this when user asks for analytics, reports, or overview.
    """
    try:
        db = SessionLocal()

        if hcp_name:
            interactions = db.query(Interaction).filter(
                Interaction.hcp_name.ilike(f"%{hcp_name}%")
            ).all()
        else:
            interactions = db.query(Interaction).all()

        db.close()

        total = len(interactions)
        if total == 0:
            return json.dumps({
                "status": "not_found",
                "message": "No interactions found."
            })

        sentiments = {"Positive": 0, "Neutral": 0, "Negative": 0}
        types = {}
        for i in interactions:
            s = i.sentiment or "Neutral"
            sentiments[s] = sentiments.get(s, 0) + 1
            t = i.interaction_type or "Meeting"
            types[t] = types.get(t, 0) + 1

        return json.dumps({
            "status": "success",
            "scope": hcp_name if hcp_name else "All HCPs",
            "total_interactions": total,
            "sentiment_breakdown": sentiments,
            "interaction_type_breakdown": types,
            "positive_rate": f"{round(sentiments['Positive'] / total * 100, 1)}%"
        })
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})


# ─────────────────────────────────────────
# LangGraph State
# ─────────────────────────────────────────
class AgentState(TypedDict):
    messages: Annotated[list, operator.add]


# ─────────────────────────────────────────
# LangGraph Setup
# ─────────────────────────────────────────
tools = [
    log_interaction,
    edit_interaction,
    get_hcp_profile,
    analyze_sentiment,
    suggest_followup,
    search_interactions,
    get_interaction_stats
]

llm_with_tools = llm.bind_tools(tools)

SYSTEM_PROMPT = """You are an AI assistant for a pharmaceutical CRM system helping field representatives manage HCP (Healthcare Professional) interactions.

You have access to 7 tools:
1. log_interaction - Log a new HCP interaction from natural language
2. edit_interaction - Edit an existing interaction by ID (interaction_id must be string of digits like "1")
3. get_hcp_profile - Get full profile and history of an HCP
4. analyze_sentiment - Analyze sentiment of interaction text
5. suggest_followup - Get AI follow-up suggestions for an HCP
6. search_interactions - Search interactions by keyword
7. get_interaction_stats - Get analytics and statistics

IMPORTANT RULES:
- For edit_interaction: interaction_id must always be a string like "1", "2", "3"
- For edit_interaction: updates must be valid JSON string like {"sentiment": "Positive"}
- Before editing, use search_interactions to find the correct interaction ID
- Always be helpful, concise, and professional
- If user says "edit Dr. Raju", first search for Dr. Raju to get the ID, then edit"""


def agent_node(state: AgentState):
    messages = [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]
    response = llm_with_tools.invoke(messages)
    return {"messages": [response]}


def should_continue(state: AgentState):
    last_message = state["messages"][-1]
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"
    return END


tool_node = ToolNode(tools)

graph = StateGraph(AgentState)
graph.add_node("agent", agent_node)
graph.add_node("tools", tool_node)
graph.set_entry_point("agent")
graph.add_conditional_edges(
    "agent",
    should_continue,
    {"tools": "tools", END: END}
)
graph.add_edge("tools", "agent")

app_graph = graph.compile()


# ─────────────────────────────────────────
# Main Run Function
# ─────────────────────────────────────────
def run_agent(message: str) -> dict:
    try:
        initial_state = {
            "messages": [HumanMessage(content=message)]
        }

        result = app_graph.invoke(initial_state)
        messages = result["messages"]

        # Final text response 
        final_response = ""
        for msg in reversed(messages):
            if hasattr(msg, "content") and isinstance(msg.content, str) and msg.content.strip():
                final_response = msg.content
                break

        # Intent detect 
        msg_lower = message.lower()
        if any(w in msg_lower for w in ["log", "met", "visited", "called", "discussed"]):
            intent = "LOG"
        elif any(w in msg_lower for w in ["edit", "update", "change", "modify"]):
            intent = "EDIT"
        elif any(w in msg_lower for w in ["profile", "history", "about dr", "about doctor"]):
            intent = "PROFILE"
        elif any(w in msg_lower for w in ["sentiment", "feeling", "tone", "analyze"]):
            intent = "SENTIMENT"
        elif any(w in msg_lower for w in ["follow", "next step", "suggest"]):
            intent = "FOLLOWUP"
        elif any(w in msg_lower for w in ["search", "find", "show", "list"]):
            intent = "SEARCH"
        elif any(w in msg_lower for w in ["stats", "analytics", "report", "count", "total"]):
            intent = "STATS"
        else:
            intent = "GENERAL"

        # Follow-up suggestions
        followup_suggestions = []
        for msg in reversed(messages):
            if hasattr(msg, "content") and isinstance(msg.content, str):
                try:
                    data = json.loads(msg.content)
                    if "followup" in data and "suggestions" in data["followup"]:
                        followup_suggestions = data["followup"]["suggestions"]
                        break
                except Exception:
                    pass

        return {
            "response": final_response or "Done!",
            "intent": intent,
            "extracted_data": {},
            "followup_suggestions": followup_suggestions
        }

    except Exception as e:
        return {
            "response": f"Agent error: {str(e)}",
            "intent": "ERROR",
            "extracted_data": {},
            "followup_suggestions": []
        }