import re
from typing import Tuple


class PIIMasker:
    """
    Detects and sanitizes Personally Identifiable Information (PII)
    including SSNs, credit card numbers, phone numbers, and email addresses.
    """

    PATTERNS = {
        "ssn": (re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), "[REDACTED_SSN]"),
        "credit_card": (
            re.compile(r"\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13}|3(?:0[0-5]|[68][0-9])[0-9]{11}|6(?:011|5[0-9]{2})[0-9]{12})\b"),
            "[REDACTED_CC]",
        ),
        "phone": (re.compile(r"\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"), "[REDACTED_PHONE]"),
        "email": (re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"), "[REDACTED_EMAIL]"),
    }

    def mask(self, text: str) -> Tuple[str, list[str]]:
        """
        Masks detected PII tokens in text.

        Returns:
            Tuple of (sanitized_text, list_of_detected_pii_types)
        """
        if not text:
            return text, []

        sanitized = text
        detected = []

        for pii_type, (pattern, replacement) in self.PATTERNS.items():
            if pattern.search(sanitized):
                detected.append(pii_type)
                sanitized = pattern.sub(replacement, sanitized)

        return sanitized, detected


pii_masker = PIIMasker()
