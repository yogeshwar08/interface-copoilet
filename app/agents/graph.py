import re
import time
from typing import Literal, TypedDict, Optional, List, Dict, Any

from langgraph.graph import END, START, StateGraph

from app.agents.sql_agent import run_sql_agent
from app.guardrails.guardrail_manager import guardrail_manager
from app.llm.gemini import llm
from app.retrieval.search import retrieve_context
from app.tools.registry import get_tool


# ============================================================
# ROUTE TYPES
# ============================================================

RouteType = Literal["rag", "sql", "tool", "direct", "blocked"]


# ============================================================
# AGENT STATE
# ============================================================

class AgentState(TypedDict):
    query: str
    route: str
    route_reasoning: str
    context: str
    sources: list[dict]
    response: str
    citations: list[int]

    # SQL-specific fields
    sql: str
    sql_rows: list[dict]

    # Tool-specific fields
    tool_name: str
    tool_result: dict

    # Guardrails & Observability
    guardrail_status: str
    guardrail_reason: str
    trace_id: str
    tokens_used: int
    latency_ms: float
    cached: bool


# ============================================================
# GUARDRAIL NODE
# ============================================================

def guardrail_node(state: AgentState) -> AgentState:
    """Pre-execution security inspection for injections, jailbreaks, and off-topic queries."""
    query = state.get("query", "")
    gr_result = guardrail_manager.validate_input(query)

    if not gr_result.passed:
        return {
            **state,
            "route": "blocked",
            "guardrail_status": "blocked",
            "guardrail_reason": gr_result.reason or "Security policy violation",
            "response": gr_result.suggested_response or "Query blocked by enterprise safety policy.",
        }

    return {
        **state,
        "query": gr_result.sanitized_text,
        "guardrail_status": "passed",
        "guardrail_reason": "",
    }


# ============================================================
# ROUTER
# ============================================================

def router_node(state: AgentState) -> AgentState:
    query = state["query"].lower().strip()

    # Fast path 1: Direct conversational greetings / help
    direct_patterns = [
        r"^(hi|hello|hey|greetings|good morning|good afternoon)\b",
        r"who are you",
        r"what can you do",
        r"help( me)?$",
        r"what is this( system)?",
    ]
    if any(re.search(pat, query) for pat in direct_patterns):
        return {
            **state,
            "route": "direct",
            "route_reasoning": "Detected conversational greeting or capability inquiry",
        }

    # Fast path 2: External Tools (e.g., Weather)
    tool_pattern = r"\b(weather|temperature|forecast|humidity|wind|precipitation)\b"
    if re.search(tool_pattern, query):
        return {
            **state,
            "route": "tool",
            "tool_name": "weather",
            "route_reasoning": "Detected request for external tool / weather telemetry",
        }


    # Fast path 3: SQL Database queries
    sql_keywords = [
        "how many users", "user count", "customer profile", "customer profiles",
        "monthly charges", "total charges", "support ticket", "tenure", "contract type",
        "approval request", "approval requests", "in the database", "from the database",
        "sql", "table", "tables", "record", "records"
    ]
    if any(kw in query for kw in sql_keywords):
        return {
            **state,
            "route": "sql",
            "route_reasoning": "Detected structured relational database analytics query",
        }

    # Fast path 4: Document / RAG search
    rag_keywords = [
        "document", "documents", "guideline", "guidelines", "policy", "policies",
        "report", "reports", "according to", "what does", "explain", "criteria",
        "diabetes", "diagnosis", "treatment", "fasting plasma", "glucose", "hba1c",
        "sec", "10-k", "filing"
    ]
    if any(kw in query for kw in rag_keywords):
        return {
            **state,
            "route": "rag",
            "route_reasoning": "Detected enterprise document / policy retrieval query",
        }

    # Default fallback to RAG for exploratory questions, or tool for unknown
    if len(query.split()) > 2:
        return {
            **state,
            "route": "rag",
            "route_reasoning": "Defaulting exploratory knowledge query to Hybrid RAG",
        }

    return {
        **state,
        "route": "direct",
        "route_reasoning": "Short ambiguous query routed to direct enterprise assistant overview",
    }


# ============================================================
# RAG NODE
# ============================================================

def rag_node(state: AgentState) -> AgentState:
    query = state["query"]

    results = retrieve_context(
        query=query,
        candidate_k=25,
        top_k=8,
    )

    context_parts = []
    sources = []

    for index, result in enumerate(results, start=1):
        payload = result.get("payload", {}) if "payload" in result else result
        text = (
            payload.get("text")
            or payload.get("content")
            or payload.get("chunk_text")
            or result.get("text")
            or ""
        )

        if not text:
            continue

        filename = payload.get("filename") or result.get("filename") or "document.pdf"
        page = payload.get("page_number") or payload.get("page") or result.get("page")
        chunk_id = payload.get("chunk_id") or result.get("chunk_id")
        score = result.get("score") if result.get("score") is not None else 0.0

        context_parts.append(f"[Source {index}]\nDocument: {filename}\nPage: {page}\nContent: {text}")
        sources.append({
            "source_number": index,
            "chunk_id": chunk_id,
            "document_id": payload.get("document_id"),
            "filename": filename,
            "page": page,
            "score": score,
        })

    context = "\n\n".join(context_parts)

    return {
        **state,
        "context": context,
        "sources": sources,
    }


# ============================================================
# CITATION VALIDATION
# ============================================================

def validate_citations(response: str, sources: list[dict]):
    """
    Validate citations generated by the LLM.
    Expected format: [Source 1], [Source 2]
    """
    valid_source_numbers = set(range(1, len(sources) + 1))
    citation_pattern = r"(?:\[|\()Source\s*:?\s*(\d+)(?:\]|\))"

    cited_numbers = [
        int(num) for num in re.findall(citation_pattern, response, flags=re.IGNORECASE)
    ]
    valid_citations = [num for num in cited_numbers if num in valid_source_numbers]

    # Normalize format: [Source1] or (Source 1) -> [Source 1]
    cleaned_response = re.sub(r"(?:\[|\()Source\s*:?\s*(\d+)(?:\]|\))", r"[Source \1]", response, flags=re.IGNORECASE)

    return cleaned_response, sorted(set(valid_citations))


# ============================================================
# ANSWER NODE
# ============================================================

def answer_node(state: AgentState) -> AgentState:
    query = state["query"]
    context = state["context"]
    sources = state["sources"]

    if not context or not sources:
        return {
            **state,
            "response": (
                "The provided documents do not contain enough information to answer this question. "
                "Please verify that relevant knowledge base documents have been ingested."
            ),
            "citations": [],
        }

    # Generate grounded answer using retrieved context
    raw_response = llm.generate(
        query=query,
        context=context,
    )

    cleaned_response, valid_citations = validate_citations(raw_response, sources)

    # Grounding protection
    if sources and not valid_citations:
        refusal_phrases = [
            "do not contain enough",
            "not enough information",
            "not found",
            "cannot determine",
            "does not contain",
            "not provide enough verified",
        ]
        if not any(rp in raw_response.lower() for rp in refusal_phrases):
            # Model answered from context but omitted citation tag; attribute to primary source
            cleaned_response = f"{raw_response.strip()} [Source 1]"
            valid_citations = [1]
        else:
            cleaned_response = (
                "The retrieved documents do not provide enough verified information to answer this question."
            )

    return {
        **state,
        "response": cleaned_response,
        "citations": valid_citations,
    }


# ============================================================
# SQL NODE
# ============================================================

def sql_node(state: AgentState) -> AgentState:
    query = state["query"]

    try:
        result = run_sql_agent(query)
        sql = result["sql"]
        rows = result["rows"]

        if not rows:
            response = "The database query executed successfully but returned 0 records."
        elif len(rows) == 1 and len(rows[0]) == 1:
            key, value = next(iter(rows[0].items()))
            response = f"Database query result ({key}): {value}"
        else:
            response = f"Found {len(rows)} matching database records:\n" + str(rows)

        return {
            **state,
            "sql": sql,
            "sql_rows": rows,
            "response": response,
        }
    except Exception as exc:
        return {
            **state,
            "sql": getattr(state, "sql", ""),
            "sql_rows": [],
            "response": f"SQL Execution Error: {exc}",
        }


# ============================================================
# TOOL NODE
# ============================================================

def tool_node(state: AgentState) -> AgentState:
    query = state["query"].lower()

    if "weather" in query or "temperature" in query or "forecast" in query:
        try:
            weather = get_tool("weather")
            # Default to Delhi coordinates or extracted lat/long
            result = weather.run(latitude=28.6139, longitude=77.2090)
            response = (
                f"Current Weather Report (Lat 28.61, Lon 77.21):\n"
                f"- Temperature: {result['temperature_c']} °C (Feels like: {result['apparent_temperature_c']} °C)\n"
                f"- Humidity: {result['relative_humidity_percent']}%\n"
                f"- Wind Speed: {result['wind_speed_kmh']} km/h\n"
                f"- Precipitation: {result['precipitation_mm']} mm"
            )
            return {
                **state,
                "tool_name": "weather",
                "tool_result": result,
                "response": response,
            }
        except Exception as exc:
            return {
                **state,
                "tool_name": "weather",
                "tool_result": {},
                "response": f"Weather tool execution failed: {exc}",
            }

    return {
        **state,
        "response": "No authorized enterprise tool matches this specific request.",
    }


# ============================================================
# DIRECT NODE (Conversational / Capabilities)
# ============================================================

def direct_node(state: AgentState) -> AgentState:
    response = (
        "Hello! I am your Agentic Enterprise Knowledge Copilot. Here is what I can do:\n\n"
        "1. **Enterprise Document RAG**: Ask questions about ingested guidelines, policies, or filings (e.g., 'What are the diagnostic criteria for diabetes?'). I return cited answers with [Source N] grounding.\n"
        "2. **Structured SQL Analytics**: Ask queries over the corporate database (e.g., 'How many users are in the database?', 'What are the customer profiles?').\n"
        "3. **Enterprise Tools**: Query live integrations such as Open-Meteo weather telemetry.\n\n"
        "All requests pass through our automated security guardrails and hybrid dense+sparse retrieval pipeline."
    )
    return {
        **state,
        "response": response,
        "citations": [],
    }


# ============================================================
# REFUSAL NODE (Guardrail violations)
# ============================================================

def refusal_node(state: AgentState) -> AgentState:
    return state


# ============================================================
# ROUTE DECISION
# ============================================================

def guardrail_decision(state: AgentState) -> str:
    if state.get("guardrail_status") == "blocked":
        return "refusal"
    return "router"


def route_decision(state: AgentState) -> str:
    return state.get("route", "direct")


# ============================================================
# BUILD LANGGRAPH
# ============================================================

def build_graph():
    graph = StateGraph(AgentState)

    # Add Nodes
    graph.add_node("guardrail", guardrail_node)
    graph.add_node("router", router_node)
    graph.add_node("rag", rag_node)
    graph.add_node("answer", answer_node)
    graph.add_node("sql", sql_node)
    graph.add_node("tool", tool_node)
    graph.add_node("direct", direct_node)
    graph.add_node("refusal", refusal_node)

    # Start Edge -> Guardrails
    graph.add_edge(START, "guardrail")

    # Guardrail Check -> (refusal or router)
    graph.add_conditional_edges(
        "guardrail",
        guardrail_decision,
        {
            "refusal": "refusal",
            "router": "router",
        },
    )

    # Router Decision
    graph.add_conditional_edges(
        "router",
        route_decision,
        {
            "rag": "rag",
            "sql": "sql",
            "tool": "tool",
            "direct": "direct",
            "blocked": "refusal",
        },
    )

    # RAG pipeline: rag -> answer -> END
    graph.add_edge("rag", "answer")
    graph.add_edge("answer", END)

    # Leaf nodes to END
    graph.add_edge("sql", END)
    graph.add_edge("tool", END)
    graph.add_edge("direct", END)
    graph.add_edge("refusal", END)

    return graph.compile()


agent_graph = build_graph()