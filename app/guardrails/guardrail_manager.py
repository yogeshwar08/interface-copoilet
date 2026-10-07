from dataclasses import dataclass, field
from typing import Literal, Optional, List

from app.config import settings
from app.guardrails.injection_detector import injection_detector
from app.guardrails.topic_guard import topic_guard
from app.guardrails.pii_masker import pii_masker


GuardrailCategory = Literal["clean", "prompt_injection", "off_topic", "pii_violation"]


@dataclass
class GuardrailResult:
    passed: bool
    category: GuardrailCategory
    reason: Optional[str] = None
    sanitized_text: str = ""
    risk_score: float = 0.0
    pii_types_detected: List[str] = field(default_factory=list)
    suggested_response: Optional[str] = None


class GuardrailManager:
    """
    Centralized Guardrails Engine for the Agentic Copilot.
    Validates user queries against adversarial prompt injection,
    enforces enterprise topic boundaries, masks sensitive PII,
    and returns standardized violation verdicts.
    """

    def __init__(self):
        self.enabled = settings.guardrails_enabled

    def validate_input(self, query: str) -> GuardrailResult:
        if not self.enabled:
            return GuardrailResult(
                passed=True,
                category="clean",
                sanitized_text=query,
                risk_score=0.0,
            )

        # 1. PII Redaction
        sanitized_query, pii_types = pii_masker.mask(query)

        # 2. Prompt Injection & Jailbreak Check
        is_injection, risk_score, injection_reason = injection_detector.detect(query)
        if is_injection:
            return GuardrailResult(
                passed=False,
                category="prompt_injection",
                reason=injection_reason,
                sanitized_text=sanitized_query,
                risk_score=risk_score,
                pii_types_detected=pii_types,
                suggested_response=(
                    "Your request could not be processed because it triggered our safety "
                    "policy regarding prompt security and instruction boundaries."
                ),
            )

        # 3. Off-Topic Boundary Check
        is_off_topic, topic_reason = topic_guard.is_off_topic(sanitized_query)
        if is_off_topic:
            return GuardrailResult(
                passed=False,
                category="off_topic",
                reason=topic_reason,
                sanitized_text=sanitized_query,
                risk_score=0.75,
                pii_types_detected=pii_types,
                suggested_response=(
                    "I am an Enterprise Knowledge Copilot specialized in organizational "
                    "documents, SQL database metrics, and approved tools. "
                    "I cannot assist with queries outside these enterprise boundaries."
                ),
            )

        return GuardrailResult(
            passed=True,
            category="clean",
            sanitized_text=sanitized_query,
            risk_score=risk_score,
            pii_types_detected=pii_types,
        )


guardrail_manager = GuardrailManager()
