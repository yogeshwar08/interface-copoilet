import asyncio
import json
import logging
import time
from pathlib import Path
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, BackgroundTasks, UploadFile, File
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

from app.agents.graph import agent_graph
from app.cache.redis_cache import cache_service
from app.database.postgres import test_connection as test_db_connection
from app.observability.tracer import tracer
from app.retrieval.indexer import index_document
from app.retrieval.vector_store import get_qdrant_client, COLLECTION_NAME


router = APIRouter(
    prefix="/api/v1",
    tags=["Enterprise Copilot"],
)


# ============================================================
# REQUEST & RESPONSE SCHEMAS
# ============================================================

class QueryRequest(BaseModel):
    query: str = Field(..., description="User question or operational query", min_length=1)
    bypass_cache: bool = Field(False, description="Whether to bypass the response cache")


class SourceReference(BaseModel):
    source_number: int
    filename: Optional[str] = None
    page: Optional[int] = None
    chunk_id: Optional[str] = None
    score: Optional[float] = None


class QueryResponse(BaseModel):
    query: str
    route: str
    response: str
    citations: List[int] = Field(default_factory=list)
    sources: List[Dict[str, Any]] = Field(default_factory=list)
    sql: Optional[str] = None
    trace_id: str
    latency_ms: float
    tokens_used: int
    cached: bool
    guardrail_status: str


def _is_cacheable_response(route: Optional[str], response: Optional[str], sources: Optional[list]) -> bool:
    """Only cache verified responses with content; never cache refusals or empty fallbacks."""
    if not response or not response.strip():
        return False
    if route == "rag" and not sources:
        return False
    refusal_markers = [
        "do not contain enough",
        "not enough information",
        "do not provide enough",
        "not enough verified information",
        "no verified information",
        "knowledge base documents have been ingested",
        "0 records",
    ]
    resp_lower = response.lower()
    if any(marker in resp_lower for marker in refusal_markers):
        return False
    return True


# ============================================================
# HEALTH & READINESS ENDPOINT
# ============================================================

_last_health_check_time = 0.0
_cached_health_result = None


def _run_health_probes():
    db_ok = test_db_connection(timeout=1)

    # Test Qdrant
    qdrant_ok = False
    try:
        q_client = get_qdrant_client()
        q_client.get_collections()
        qdrant_ok = True
    except Exception:
        qdrant_ok = False

    cache_stats = cache_service.stats

    jaeger_status = tracer.check_jaeger_status()

    return {
        "status": "healthy" if db_ok or qdrant_ok else "degraded",
        "service": "agentic-enterprise-copilot",
        "version": "1.0.0",
        "components": {
            "database_postgresql": "connected" if db_ok else "unreachable",
            "vector_store_qdrant": "ready" if qdrant_ok else "degraded",
            "cache_layer": cache_stats["backend"],
            "jaeger_tracing": jaeger_status,
        },
    }


@router.get("/health")
async def health_check():
    """Detailed health probe assessing all enterprise copilot subsystems."""
    global _last_health_check_time, _cached_health_result
    now = time.time()
    if _cached_health_result and (now - _last_health_check_time < 5.0):
        return _cached_health_result

    result = await asyncio.to_thread(_run_health_probes)
    _cached_health_result = result
    _last_health_check_time = now
    return result


# ============================================================
# OBSERVABILITY METRICS ENDPOINT
# ============================================================

@router.get("/metrics")
async def get_system_metrics():
    """Real-time observability metrics: latency, token consumption, cost, and routing distribution."""
    metrics = tracer.get_metrics_summary()
    cache_stats = cache_service.stats
    return {
        "observability": metrics,
        "cache": cache_stats,
    }


@router.get("/traces")
async def get_traces():
    """Returns recent query traces with spans, latency breakdowns, and token auditing."""
    return {
        "total": len(tracer.recent_traces),
        "traces": [t.to_dict() for t in reversed(tracer.recent_traces)],
        "jaeger_status": tracer.check_jaeger_status(),
    }


# ============================================================
# SYNCHRONOUS QUERY ENDPOINT (WITH CACHING & OBSERVABILITY)
# ============================================================

@router.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    """
    Executes the multi-agent graph with caching, guardrails,
    intelligent routing, grounding, and trace auditing.
    """
    start_time = time.perf_counter()
    query_text = request.query.strip()

    # 1. Check Cache Layer
    if not request.bypass_cache:
        cached_result = cache_service.get(query_text)
        if cached_result:
            if not _is_cacheable_response(
                cached_result.get("route"),
                cached_result.get("response"),
                cached_result.get("sources"),
            ):
                cache_service.delete(query_text)
                cached_result = None

        if cached_result:
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
            # Record fast cache hit trace
            trace = tracer.start_trace(query_text)
            trace.route = cached_result.get("route", "cached")
            trace.cached = True
            trace.total_tokens = cached_result.get("tokens_used", 0)
            tracer.end_trace(trace)

            return QueryResponse(
                query=query_text,
                route=cached_result.get("route", "cached"),
                response=cached_result.get("response", ""),
                citations=cached_result.get("citations", []),
                sources=cached_result.get("sources", []),
                sql=cached_result.get("sql"),
                trace_id=trace.trace_id,
                latency_ms=latency_ms,
                tokens_used=cached_result.get("tokens_used", 0),
                cached=True,
                guardrail_status=cached_result.get("guardrail_status", "passed"),
            )

    # 2. Start Observability Trace
    trace = tracer.start_trace(query_text)

    # 3. Initialize Agent Graph State
    initial_state = {
        "query": query_text,
        "route": "",
        "route_reasoning": "",
        "context": "",
        "sources": [],
        "response": "",
        "citations": [],
        "sql": "",
        "sql_rows": [],
        "tool_name": "",
        "tool_result": {},
        "guardrail_status": "passed",
        "guardrail_reason": "",
        "trace_id": trace.trace_id,
        "tokens_used": 0,
        "latency_ms": 0.0,
        "cached": False,
    }

    # 4. Invoke LangGraph Execution Engine
    result = agent_graph.invoke(initial_state)

    latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

    # 5. Calculate Token Consumption & Trace Recording
    prompt_tokens = tracer.estimate_tokens(query_text + (result.get("context") or ""))
    completion_tokens = tracer.estimate_tokens(result.get("response") or "")
    total_tokens = prompt_tokens + completion_tokens

    trace.route = result.get("route", "unknown")
    trace.prompt_tokens = prompt_tokens
    trace.completion_tokens = completion_tokens
    trace.total_tokens = total_tokens
    trace.guardrail_status = result.get("guardrail_status", "passed")
    tracer.end_trace(trace)

    # 6. Store in Cache (only if verified, clean, non-refusal answer)
    route_selected = result.get("route", "direct")
    response_text = result.get("response", "")
    sources_list = result.get("sources", [])
    if (
        result.get("guardrail_status") == "passed"
        and route_selected != "blocked"
        and _is_cacheable_response(route_selected, response_text, sources_list)
    ):
        cache_data = {
            "route": route_selected,
            "response": response_text,
            "citations": result.get("citations", []),
            "sources": sources_list,
            "sql": result.get("sql"),
            "tokens_used": total_tokens,
            "guardrail_status": "passed",
        }
        cache_service.set(query_text, cache_data)

    return QueryResponse(
        query=query_text,
        route=result.get("route", "direct"),
        response=result.get("response", ""),
        citations=result.get("citations", []),
        sources=result.get("sources", []),
        sql=result.get("sql") if result.get("sql") else None,
        trace_id=trace.trace_id,
        latency_ms=latency_ms,
        tokens_used=total_tokens,
        cached=False,
        guardrail_status=result.get("guardrail_status", "passed"),
    )


# ============================================================
# STREAMING QUERY ENDPOINT (SERVER-SENT EVENTS - SSE)
# ============================================================

@router.post("/query/stream")
async def query_stream(request: QueryRequest):
    """
    Streaming SSE endpoint delivering progressive tokens,
    sub-agent routing decisions, and citation verification in real time.

    Uses a concurrent keepalive heartbeat to prevent Render's 55-second proxy
    timeout from closing the SSE connection before the agent finishes.
    """
    query_text = request.query.strip()
    start_time = time.perf_counter()
    trace = tracer.start_trace(query_text)

    async def event_generator():
        try:
            # Event 1: Init / Guardrail Check
            yield f"event: status\ndata: {json.dumps({'message': 'Executing security guardrails & query router...'})}\n\n"
            await asyncio.sleep(0.02)

            # Check cache first — instant return, no timeout risk
            if not request.bypass_cache:
                cached_data = cache_service.get(query_text)
                if cached_data:
                    if not _is_cacheable_response(
                        cached_data.get("route"),
                        cached_data.get("response"),
                        cached_data.get("sources"),
                    ):
                        cache_service.delete(query_text)
                        cached_data = None

                if cached_data:
                    yield f"event: route\ndata: {json.dumps({'route': cached_data.get('route'), 'cached': True})}\n\n"
                    full_response = cached_data.get("response", "")
                    words = full_response.split(" ")
                    for i in range(0, len(words), 3):
                        chunk = " ".join(words[i : i + 3]) + " "
                        yield f"event: token\ndata: {json.dumps({'token': chunk})}\n\n"
                        await asyncio.sleep(0.015)

                    if cached_data.get("citations"):
                        yield f"event: citations\ndata: {json.dumps({'citations': cached_data.get('citations')})}\n\n"

                    total_latency = round((time.perf_counter() - start_time) * 1000, 2)
                    yield f"event: done\ndata: {json.dumps({'trace_id': trace.trace_id, 'latency_ms': total_latency, 'cached': True})}\n\n"
                    return

            # Build initial LangGraph state
            initial_state = {
                "query": query_text,
                "route": "",
                "route_reasoning": "",
                "context": "",
                "sources": [],
                "response": "",
                "citations": [],
                "sql": "",
                "sql_rows": [],
                "tool_name": "",
                "tool_result": {},
                "guardrail_status": "passed",
                "guardrail_reason": "",
                "trace_id": trace.trace_id,
                "tokens_used": 0,
                "latency_ms": 0.0,
                "cached": False,
            }

            # ── Run agent in a background asyncio Task ──────────────────────────
            # This allows us to yield keepalive comment pings to Render's proxy
            # every 15 seconds while the agent is processing, preventing the 502.
            agent_task = asyncio.create_task(
                asyncio.to_thread(agent_graph.invoke, initial_state)
            )

            # Keepalive loop: yield SSE comment pings every 15s until agent done
            KEEPALIVE_INTERVAL = 15  # seconds
            ping_count = 0
            while not agent_task.done():
                try:
                    await asyncio.wait_for(
                        asyncio.shield(agent_task), timeout=KEEPALIVE_INTERVAL
                    )
                except asyncio.TimeoutError:
                    ping_count += 1
                    # SSE comment lines (": ...") are invisible to the client but
                    # flush bytes through Render's proxy, resetting its idle timer
                    yield f": keepalive {ping_count}\n\n"

            # Retrieve result (re-raises if the task raised an exception)
            result = agent_task.result()
            # ────────────────────────────────────────────────────────────────────

            route_selected = result.get("route", "direct")
            yield f"event: route\ndata: {json.dumps({'route': route_selected, 'reasoning': result.get('route_reasoning')})}\n\n"
            await asyncio.sleep(0.02)

            # If RAG route, emit source discovery event
            if route_selected == "rag" and result.get("sources"):
                yield f"event: sources\ndata: {json.dumps({'sources_found': len(result['sources'])})}\n\n"

            # Stream response content word-by-word for smooth UX
            full_response = result.get("response", "")
            words = full_response.split(" ")
            for i in range(0, len(words), 4):
                chunk = " ".join(words[i : i + 4]) + " "
                yield f"event: token\ndata: {json.dumps({'token': chunk})}\n\n"
                await asyncio.sleep(0.02)

            # Emit citations if any
            if result.get("citations"):
                yield f"event: citations\ndata: {json.dumps({'citations': result.get('citations')})}\n\n"

            total_latency = round((time.perf_counter() - start_time) * 1000, 2)
            prompt_tokens = tracer.estimate_tokens(query_text + (result.get("context") or ""))
            completion_tokens = tracer.estimate_tokens(full_response)
            total_tokens = prompt_tokens + completion_tokens

            trace.route = route_selected
            trace.prompt_tokens = prompt_tokens
            trace.completion_tokens = completion_tokens
            trace.total_tokens = total_tokens
            tracer.end_trace(trace)

            # Cache the clean result (only if verified, non-refusal answer)
            sources_list = result.get("sources", [])
            if (
                result.get("guardrail_status") == "passed"
                and route_selected != "blocked"
                and _is_cacheable_response(route_selected, full_response, sources_list)
            ):
                cache_service.set(
                    query_text,
                    {
                        "route": route_selected,
                        "response": full_response,
                        "citations": result.get("citations", []),
                        "sources": sources_list,
                        "sql": result.get("sql"),
                        "tokens_used": total_tokens,
                        "guardrail_status": "passed",
                    },
                )

            yield f"event: done\ndata: {json.dumps({'trace_id': trace.trace_id, 'latency_ms': total_latency, 'tokens_used': total_tokens, 'cached': False})}\n\n"

        except Exception as exc:
            logger.error(f"Streaming error for query '{query_text[:60]}': {exc}")
            yield f"event: error\ndata: {json.dumps({'error': str(exc)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            # Disable nginx/Render proxy buffering so bytes flush immediately
            "X-Accel-Buffering": "no",
        },
    )


# ============================================================
# CACHE MANAGEMENT ENDPOINT
# ============================================================

@router.post("/cache/clear")
async def clear_cache():
    """Flushes active query caches across Redis and in-memory stores."""
    cache_service.clear()
    return {"status": "success", "message": "Query cache successfully cleared"}


# ============================================================
# DOCUMENT INGESTION & UPLOAD ENDPOINTS
# ============================================================

@router.get("/documents")
async def list_documents():
    """Lists all enterprise documents present in data/raw storage."""
    raw_dir = Path("data/raw")
    if not raw_dir.exists():
        raw_dir.mkdir(parents=True, exist_ok=True)

    docs = []
    for f in raw_dir.glob("*.pdf"):
        size_kb = round(f.stat().st_size / 1024, 1)
        docs.append({
            "filename": f.name,
            "size_kb": size_kb,
            "path": str(f),
        })
    return {"documents": docs, "total": len(docs)}


@router.post("/documents/upload")
async def upload_document(file: UploadFile = File(...)):
    """
    Accepts a PDF document upload, stores it in data/raw,
    and indexes it into Qdrant vector store and BM25 search indices.
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Only PDF documents (.pdf) are supported for enterprise ingestion.",
        )

    raw_dir = Path("data/raw")
    raw_dir.mkdir(parents=True, exist_ok=True)
    destination_path = raw_dir / file.filename

    # Save uploaded file
    try:
        content = await file.read()
        with open(destination_path, "wb") as f:
            f.write(content)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {exc}")

    # Index document in worker thread
    try:
        indexing_result = await asyncio.to_thread(index_document, str(destination_path))
        return {
            "status": "success",
            "message": f"Successfully ingested and indexed '{file.filename}'",
            "document_id": indexing_result.get("document_id"),
            "filename": indexing_result.get("filename"),
            "chunks_indexed": indexing_result.get("chunks_indexed", 0),
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Indexing failed: {exc}")