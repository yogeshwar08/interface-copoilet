import re
from typing import Tuple


# Comprehensive known prompt injection and jailbreak signatures
INJECTION_PATTERNS = [
    # Direct instruction overrides
    r"ignore\s+(all\s+)?(previous\s+|prior\s+|above\s+)?(instructions|directives|prompts|rules)",
    r"disregard\s+(all\s+)?(previous\s+|prior\s+|above\s+)?(instructions|directives|prompts|rules)",
    r"forget\s+(all\s+)?(previous\s+|prior\s+|above\s+)?(instructions|prompts|rules)",
    r"override\s+(system\s+)?(instructions|prompt|rules)",
    r"bypass\s+(safety|content|system)\s+(filter|guidelines|restrictions|guardrails)",

    # Persona / Jailbreak modes
    r"you\s+are\s+now\s+(dan|an\s+unrestricted|evil|unfiltered|jailbroken)",
    r"do\s+anything\s+now",
    r"developer\s+mode\s+(enabled|on|activate)",
    r"act\s+as\s+(an?\s+unrestricted|a\s+hacker|an?\s+evil|godmode)",
    r"pretend\s+there\s+are\s+no\s+rules",
    r"simulate\s+a\s+world\s+without\s+rules",

    # System prompt exfiltration
    r"(reveal|print|repeat|show|output|leak|dump)\s+(the\s+)?(system\s+prompt|initial\s+prompt|developer\s+instructions|system\s+instructions|prompt)",
    r"what\s+(is|are)\s+your\s+(exact\s+)?(system\s+instructions|system\s+prompt|secret\s+instructions)",
    r"what\s+were\s+you\s+told\s+before\s+this",

    # Delimiter / Control token injection
    r"<\s*\|?\s*(system|im_start|im_end|endoftext|instruction)\s*\|?\s*>",
    r"\[\s*system\s*\]",
    r"###\s*(instruction|system|human|override):?",
    r"```\s*system",

    # Base64 or obfuscation markers
    r"base64\s*decode\s*and\s*execute",
    r"rot13\s*and\s*run",
]


class PromptInjectionDetector:
    """
    Detects adversarial prompt injections, jailbreaks, system prompt exfiltration,
    and control token delimiters.
    """

    def __init__(self, strictness: float = 0.85):
        self.strictness = strictness
        self.compiled_patterns = [
            re.compile(p, re.IGNORECASE) for p in INJECTION_PATTERNS
        ]

    def detect(self, text: str) -> Tuple[bool, float, str]:
        """
        Analyzes the query for injection attempts.

        Returns:
            Tuple of (is_injection: bool, risk_score: float, matched_reason: str)
        """
        if not text:
            return False, 0.0, "Empty text"

        normalized = text.strip()
        matched_reasons = []

        # Check regex patterns
        for pattern in self.compiled_patterns:
            match = pattern.search(normalized)
            if match:
                matched_reasons.append(f"Matched adversarial pattern: '{match.group(0)}'")

        # Check for abnormal delimiter frequency or prompt wrapping attempts
        suspicious_delimiters = ["###", "---", "===", "</system>", "[SYSTEM]"]
        delimiter_hits = sum(1 for d in suspicious_delimiters if d.lower() in normalized.lower())
        if delimiter_hits >= 2:
            matched_reasons.append("Excessive system delimiters detected")

        # Calculate risk score
        risk_score = 0.0
        if matched_reasons:
            # Base risk starts at 0.9 for direct pattern hit
            risk_score = min(1.0, 0.85 + (len(matched_reasons) * 0.05))

        is_injection = risk_score >= self.strictness

        reason = "; ".join(matched_reasons) if is_injection else "No injection detected"
        return is_injection, risk_score, reason


injection_detector = PromptInjectionDetector()
