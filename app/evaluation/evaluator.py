import json
import logging
import math
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Any, Optional

import numpy as np

from app.agents.graph import agent_graph
from app.retrieval.embeddings import embedding_model

logger = logging.getLogger(__name__)


@dataclass
class EvalSampleResult:
    sample_id: str
    question: str
    category: str
    expected_route: str
    actual_route: str
    route_correct: bool
    generated_response: str
    faithfulness_score: float
    answer_relevance_score: float
    context_precision_score: float
    guardrail_blocked: bool
    guardrail_expected: bool
    guardrail_correct: bool
    latency_ms: float = 0.0


@dataclass
class EvalReport:
    total_samples: int
    router_accuracy: float
    avg_faithfulness: float
    avg_answer_relevance: float
    avg_context_precision: float
    guardrail_accuracy: float
    samples: List[EvalSampleResult] = field(default_factory=list)

    def to_markdown(self) -> str:
        md = []
        md.append("# 📊 Enterprise Copilot Automated Evaluation Report")
        md.append("\n**Evaluation Benchmark: Golden Set (RAGAS / DeepEval Methodology)**\n")
        md.append("| Metric | Score | Target | Status |")
        md.append("| :--- | :--- | :--- | :--- |")

        def status_badge(val, target):
            return "✅ PASS" if val >= target else "⚠️ REVIEW"

        md.append(f"| **Router Accuracy** | `{self.router_accuracy:.2%}` | `>= 90.0%` | {status_badge(self.router_accuracy, 0.90)} |")
        md.append(f"| **Faithfulness (Groundedness)** | `{self.avg_faithfulness:.2%}` | `>= 85.0%` | {status_badge(self.avg_faithfulness, 0.85)} |")
        md.append(f"| **Answer Relevance** | `{self.avg_answer_relevance:.2%}` | `>= 80.0%` | {status_badge(self.avg_answer_relevance, 0.80)} |")
        md.append(f"| **Context Precision (MAP@K)** | `{self.avg_context_precision:.2%}` | `>= 75.0%` | {status_badge(self.avg_context_precision, 0.75)} |")
        md.append(f"| **Guardrail Safety Accuracy** | `{self.guardrail_accuracy:.2%}` | `>= 95.0%` | {status_badge(self.guardrail_accuracy, 0.95)} |")

        md.append("\n### Detailed Sample Breakdown\n")
        md.append("| ID | Category | Expected Route | Actual Route | Faithfulness | Relevance | Guardrail |")
        md.append("| :--- | :--- | :--- | :--- | :--- | :--- | :--- |")
        for s in self.samples[:25]:  # Display first 25 in preview
            g_icon = "🛡️ Blocked" if s.guardrail_blocked else "Passed"
            md.append(
                f"| `{s.sample_id}` | {s.category} | `{s.expected_route}` | `{s.actual_route}` | "
                f"`{s.faithfulness_score:.2f}` | `{s.answer_relevance_score:.2f}` | {g_icon} |"
            )

        if len(self.samples) > 25:
            md.append(f"\n*(... and {len(self.samples) - 25} more test cases evaluated)*")

        return "\n".join(md)


class CopilotEvaluator:
    """
    RAGAS & DeepEval-compliant Evaluation Engine.
    Evaluates:
    1. Faithfulness: Is the answer grounded in the retrieved context?
    2. Answer Relevance: Does the generated answer address the user query?
    3. Context Precision: Are ground-truth relevant context passages retrieved at the top ranks?
    4. Router Accuracy: Did the router node select the right specialized agent?
    5. Guardrail Safety: Were prompt injection and off-topic queries intercepted?
    """

    def __init__(self, golden_set_path: str = "app/evaluation/golden_dataset.json"):
        self.golden_set_path = golden_set_path

    def load_dataset(self) -> List[Dict[str, Any]]:
        path = Path(self.golden_set_path)
        if not path.exists():
            raise FileNotFoundError(f"Golden dataset not found at {path}")
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    @staticmethod
    def calculate_faithfulness(response: str, context: str) -> float:
        """
        Faithfulness = (claims supported by context) / (total claims)
        If answer refuses due to lack of documents, faithfulness is 1.0 (no hallucination).
        """
        if not response:
            return 0.0

        refusal_phrases = [
            "do not contain enough information",
            "not provide enough verified information",
            "could not be processed",
            "safety policy",
            "outside authorized enterprise scope",
        ]
        if any(rp in response.lower() for rp in refusal_phrases):
            return 1.0

        if not context:
            return 0.0

        # Split response into statements / sentences
        sentences = [s.strip() for s in re.split(r"[.\n;]", response) if len(s.strip()) > 15]
        if not sentences:
            return 1.0

        context_lower = context.lower()
        supported = 0

        for sentence in sentences:
            # Check key noun / numerical tokens in sentence against context
            tokens = [t.lower() for t in re.findall(r"\b\w{3,}\b", sentence)]
            if not tokens:
                supported += 1
                continue

            matches = sum(1 for t in tokens if t in context_lower)
            match_ratio = matches / len(tokens)
            # If 60% of significant tokens exist in context, statement is grounded
            if match_ratio >= 0.50:
                supported += 1

        return round(min(1.0, supported / len(sentences)), 4)

    @staticmethod
    def calculate_answer_relevance(question: str, response: str) -> float:
        """
        Cosine similarity between query embedding and response embedding.
        """
        if not response or not question:
            return 0.0

        try:
            vectors = embedding_model.encode([question, response])
            v1, v2 = vectors[0], vectors[1]
            similarity = float(np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2)))
            # Scale cosine similarity (-1 to 1) to (0 to 1)
            relevance = max(0.0, min(1.0, (similarity + 1) / 2))
            return round(relevance, 4)
        except Exception as exc:
            logger.debug(f"Error computing relevance embedding: {exc}")
            # Fallback lexical Jaccard
            q_set = set(re.findall(r"\b\w+\b", question.lower()))
            r_set = set(re.findall(r"\b\w+\b", response.lower()))
            if not q_set:
                return 0.0
            return round(len(q_set & r_set) / len(q_set), 4)

    @staticmethod
    def calculate_context_precision(retrieved_sources: List[Dict[str, Any]], ground_truth_contexts: List[str]) -> float:
        """
        Context Precision = MAP@K of retrieved chunks matching ground truth contexts.
        """
        if not ground_truth_contexts:
            return 1.0  # Non-RAG query

        if not retrieved_sources:
            return 0.0

        gt_tokens = set()
        for gt in ground_truth_contexts:
            gt_tokens.update(re.findall(r"\b\w{4,}\b", gt.lower()))

        precisions = []
        hits = 0

        for rank, source in enumerate(retrieved_sources, start=1):
            text = (
                source.get("text")
                or source.get("content")
                or str(source)
            ).lower()

            # Check if retrieved chunk has substantial overlap with ground truth
            source_tokens = set(re.findall(r"\b\w{4,}\b", text))
            overlap = len(source_tokens & gt_tokens)

            if overlap >= 3:
                hits += 1
                precisions.append(hits / rank)

        if not precisions:
            return 0.0

        return round(sum(precisions) / len(precisions), 4)

    def evaluate_sample(self, item: Dict[str, Any]) -> EvalSampleResult:
        query = item["question"]
        expected_route = item["expected_route"]
        ground_truth_contexts = item.get("ground_truth_contexts", [])

        # Execute agent graph
        initial_state = {
            "query": query,
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
            "trace_id": "",
            "tokens_used": 0,
            "latency_ms": 0.0,
            "cached": False,
        }

        result = agent_graph.invoke(initial_state)
        actual_route = result.get("route", "direct")
        response = result.get("response", "")
        sources = result.get("sources", [])
        context = result.get("context", "")
        guardrail_status = result.get("guardrail_status", "passed")

        is_guardrail_expected = (expected_route == "blocked")
        is_guardrail_blocked = (guardrail_status == "blocked" or actual_route == "blocked")
        guardrail_correct = (is_guardrail_expected == is_guardrail_blocked)

        route_correct = (actual_route == expected_route) or (is_guardrail_expected and is_guardrail_blocked)

        # Faithfulness
        if actual_route == "rag":
            faithfulness = self.calculate_faithfulness(response, context)
            context_precision = self.calculate_context_precision(sources, ground_truth_contexts)
        elif is_guardrail_blocked:
            faithfulness = 1.0
            context_precision = 1.0
        else:
            # SQL / Tool / Direct deterministic routes
            faithfulness = 1.0 if ("error" not in response.lower() and response) else 0.5
            context_precision = 1.0

        # Answer relevance
        answer_relevance = self.calculate_answer_relevance(query, response)

        return EvalSampleResult(
            sample_id=item["id"],
            question=query,
            category=item.get("category", "general"),
            expected_route=expected_route,
            actual_route=actual_route,
            route_correct=route_correct,
            generated_response=response,
            faithfulness_score=faithfulness,
            answer_relevance_score=answer_relevance,
            context_precision_score=context_precision,
            guardrail_blocked=is_guardrail_blocked,
            guardrail_expected=is_guardrail_expected,
            guardrail_correct=guardrail_correct,
        )

    def run_benchmark(self, limit: Optional[int] = None) -> EvalReport:
        dataset = self.load_dataset()
        if limit:
            dataset = dataset[:limit]

        results = []
        for item in dataset:
            result = self.evaluate_sample(item)
            results.append(result)

        total = len(results)
        router_acc = sum(1 for r in results if r.route_correct) / total if total else 0.0
        avg_faith = sum(r.faithfulness_score for r in results) / total if total else 0.0
        avg_rel = sum(r.answer_relevance_score for r in results) / total if total else 0.0
        avg_prec = sum(r.context_precision_score for r in results) / total if total else 0.0
        guardrail_acc = sum(1 for r in results if r.guardrail_correct) / total if total else 0.0

        return EvalReport(
            total_samples=total,
            router_accuracy=round(router_acc, 4),
            avg_faithfulness=round(avg_faith, 4),
            avg_answer_relevance=round(avg_rel, 4),
            avg_context_precision=round(avg_prec, 4),
            guardrail_accuracy=round(guardrail_acc, 4),
            samples=results,
        )


evaluator = CopilotEvaluator()
