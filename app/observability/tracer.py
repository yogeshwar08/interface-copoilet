import os
import time
import uuid
import logging
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List

from app.config import settings

logger = logging.getLogger(__name__)

# Approximate pricing per 1M tokens for Gemini Flash / standard enterprise LLMs
COST_PER_1M_INPUT = 0.075  # $0.075 / 1M prompt tokens
COST_PER_1M_OUTPUT = 0.30   # $0.30 / 1M output tokens


@dataclass
class SpanRecord:
    name: str
    start_time: float
    end_time: Optional[float] = None
    duration_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class QueryTrace:
    trace_id: str
    query: str
    route: str = "unknown"
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    total_latency_ms: float = 0.0
    spans: List[SpanRecord] = field(default_factory=list)
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0
    cached: bool = False
    guardrail_status: str = "passed"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def finish(self):
        self.end_time = time.time()
        self.total_latency_ms = round((self.end_time - self.start_time) * 1000, 2)
        # Compute cost
        input_cost = (self.prompt_tokens / 1_000_000) * COST_PER_1M_INPUT
        output_cost = (self.completion_tokens / 1_000_000) * COST_PER_1M_OUTPUT
        self.estimated_cost_usd = round(input_cost + output_cost, 6)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "query": self.query,
            "route": self.route,
            "total_latency_ms": self.total_latency_ms,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "estimated_cost_usd": self.estimated_cost_usd,
            "cached": self.cached,
            "guardrail_status": self.guardrail_status,
            "spans": [
                {
                    "name": s.name,
                    "duration_ms": s.duration_ms,
                    "metadata": s.metadata,
                }
                for s in self.spans
            ],
            "metadata": self.metadata,
        }


class ObservabilityService:
    """
    Central Observability & Tracing engine.
    Supports LangSmith tracing, latency monitoring per component,
    token consumption, cost auditing, and rolling system metrics.
    """

    def __init__(self):
        self.enabled = True
        self.recent_traces: List[QueryTrace] = []
        self._max_recent = 200

        # Configure LangSmith if enabled in settings
        if settings.langsmith_tracing and settings.langsmith_api_key:
            os.environ["LANGCHAIN_TRACING_V2"] = "true"
            os.environ["LANGCHAIN_API_KEY"] = settings.langsmith_api_key
            os.environ["LANGCHAIN_PROJECT"] = settings.langsmith_project
            os.environ["LANGCHAIN_ENDPOINT"] = settings.langsmith_endpoint
            logger.info(f"LangSmith distributed tracing enabled for project: {settings.langsmith_project}")

    def start_trace(self, query: str) -> QueryTrace:
        trace = QueryTrace(
            trace_id=str(uuid.uuid4()),
            query=query,
        )
        return trace

    def record_span(self, trace: QueryTrace, name: str, duration_ms: float, metadata: Optional[Dict[str, Any]] = None):
        span = SpanRecord(
            name=name,
            start_time=0.0,
            end_time=0.0,
            duration_ms=round(duration_ms, 2),
            metadata=metadata or {},
        )
        trace.spans.append(span)

    def end_trace(self, trace: QueryTrace):
        trace.finish()
        self.recent_traces.append(trace)
        if len(self.recent_traces) > self._max_recent:
            self.recent_traces.pop(0)

        logger.info(
            f"[TRACE {trace.trace_id[:8]}] route={trace.route} "
            f"latency={trace.total_latency_ms}ms tokens={trace.total_tokens} "
            f"cost=${trace.estimated_cost_usd} cached={trace.cached}"
        )

        # Asynchronously dispatch to Jaeger OTLP endpoint if enabled
        if settings.jaeger_enabled and settings.jaeger_endpoint:
            self._dispatch_to_jaeger(trace)

    def _dispatch_to_jaeger(self, trace: QueryTrace):
        """Dispatches OpenTelemetry formatted trace payload to Jaeger OTLP HTTP collector."""
        try:
            import httpx
            import threading

            def send():
                try:
                    payload = {
                        "resourceSpans": [
                            {
                                "resource": {
                                    "attributes": [
                                        {"key": "service.name", "value": {"stringValue": "agentic-enterprise-copilot"}},
                                        {"key": "service.version", "value": {"stringValue": settings.app_version}},
                                        {"key": "deployment.environment", "value": {"stringValue": settings.environment}},
                                    ]
                                },
                                "scopeSpans": [
                                    {
                                        "scope": {"name": "app.observability.tracer"},
                                        "spans": [
                                            {
                                                "traceId": trace.trace_id.replace("-", "").ljust(32, "0")[:32],
                                                "spanId": trace.trace_id.replace("-", "").ljust(16, "0")[:16],
                                                "name": f"Query: {trace.route}",
                                                "kind": 1,
                                                "startTimeUnixNano": int(trace.start_time * 1e9),
                                                "endTimeUnixNano": int((trace.end_time or trace.start_time) * 1e9),
                                                "attributes": [
                                                    {"key": "query", "value": {"stringValue": trace.query[:200]}},
                                                    {"key": "route", "value": {"stringValue": trace.route}},
                                                    {"key": "cached", "value": {"boolValue": trace.cached}},
                                                    {"key": "total_tokens", "value": {"intValue": trace.total_tokens}},
                                                    {"key": "cost_usd", "value": {"doubleValue": trace.estimated_cost_usd}},
                                                    {"key": "guardrail_status", "value": {"stringValue": trace.guardrail_status}},
                                                ],
                                                "status": {"code": 1},
                                            }
                                        ],
                                    }
                                ],
                            }
                        ]
                    }
                    with httpx.Client(timeout=1.0) as client:
                        client.post(
                            settings.jaeger_endpoint,
                            json=payload,
                            headers={"Content-Type": "application/json"},
                        )
                except Exception as exc:
                    logger.debug(f"Jaeger export skipped (collector unavailable): {exc}")

            threading.Thread(target=send, daemon=True).start()
        except Exception:
            pass

    def check_jaeger_status(self) -> str:
        """Probes Jaeger collector / UI availability."""
        if not settings.jaeger_enabled:
            return "disabled"
        try:
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(0.5)
            result = sock.connect_ex((settings.jaeger_host, settings.jaeger_port))
            sock.close()
            return "ready" if result == 0 else "unreachable"
        except Exception:
            return "unreachable"

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """Rough token approximation (avg 4 chars per token)."""
        if not text:
            return 0
        return max(1, len(text) // 4)

    def get_metrics_summary(self) -> Dict[str, Any]:
        """Provides real-time system metrics for observability dashboard."""
        if not self.recent_traces:
            return {
                "total_queries": 0,
                "avg_latency_ms": 0.0,
                "total_tokens_consumed": 0,
                "total_cost_usd": 0.0,
                "cache_hit_ratio": 0.0,
                "route_distribution": {},
                "jaeger_status": self.check_jaeger_status(),
            }

        total = len(self.recent_traces)
        avg_latency = sum(t.total_latency_ms for t in self.recent_traces) / total
        total_tokens = sum(t.total_tokens for t in self.recent_traces)
        total_cost = sum(t.estimated_cost_usd for t in self.recent_traces)
        cache_hits = sum(1 for t in self.recent_traces if t.cached)

        route_counts = {}
        for t in self.recent_traces:
            route_counts[t.route] = route_counts.get(t.route, 0) + 1

        return {
            "total_queries": total,
            "avg_latency_ms": round(avg_latency, 2),
            "total_tokens_consumed": total_tokens,
            "total_cost_usd": round(total_cost, 6),
            "cache_hit_ratio": round(cache_hits / total, 4),
            "route_distribution": route_counts,
            "jaeger_status": self.check_jaeger_status(),
        }


tracer = ObservabilityService()

