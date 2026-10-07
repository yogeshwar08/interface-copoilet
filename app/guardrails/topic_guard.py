import re
from typing import Tuple


# Prohibited domains for enterprise assistant
EXPLICIT_OFF_TOPIC_PATTERNS = [
    # Creative fiction / roleplay unrelated to enterprise
    r"\b(poem|poetry|fanfiction|romance\s+novel|screenplay|erotica|fairy\s+tale|bedtime\s+story)\b",
    r"(write|compose|generate|create)\s+.*?\b(poem|song|rap|fanfiction|romance|erotica|story|screenplay)\b",

    # Malicious activities / exploitation
    r"\b(hack|crack|ddos|exploit|phish|ransomware|malware|keylogger|rootkit|trojan)\b",
    r"(how\s+to\s+)?(hack|crack|ddos|exploit|phish|steal|bypass\s+passwords)",
    r"(build|make)\s+(a\s+)?(bomb|weapon|explosive)",

    # Academic dishonesty / unrelated homework
    r"\b(solve\s+my\s+homework|admission\s+essay)\b",
    r"(math|physics|calculus|chemistry)\s+homework",

    # Unrelated personal advice / entertainment
    r"\b(dating|marriage\s+advice|horoscope|astrology|zodiac|tarot)\b",
    r"who\s+is\s+the\s+best\s+(celebrity|actor|singer|footballer|cricketer)",
]


# Permitted enterprise business domains
ENTERPRISE_DOMAIN_KEYWORDS = [
    # Document / Policy / Clinical RAG
    "document", "doc", "policy", "guideline", "clinical", "diabetes", "medical",
    "report", "compliance", "standard", "procedure", "sec", "filing", "10-k", "10-q",
    "annual", "quarterly", "financial", "revenue", "ebitda", "audit", "protocol",
    "criteria", "diagnosis", "treatment", "hba1c", "glucose", "patient", "care",

    # SQL Analytics & Database
    "user", "users", "customer", "customers", "profile", "profiles", "table",
    "database", "sql", "record", "records", "count", "average", "charges",
    "tenure", "approval", "approvals", "status", "tickets", "contract", "payment",

    # Enterprise Tools & Utilities
    "weather", "temperature", "forecast", "humidity", "system", "health", "api", "copilot",

    # General Business & Productivity
    "summary", "summarize", "explain", "help", "overview", "what is", "how do I",
    "hello", "hi", "hey", "who are you", "what can you do"
]


class TopicGuard:
    """
    Enforces enterprise boundary policy.
    Blocks queries that attempt to use the copilot for creative writing,
    malware development, political commentary, or unrelated personal hobbies.
    """

    def __init__(self):
        self.prohibited_patterns = [
            re.compile(p, re.IGNORECASE) for p in EXPLICIT_OFF_TOPIC_PATTERNS
        ]

    def is_off_topic(self, text: str) -> Tuple[bool, str]:
        """
        Validates whether a query falls within authorized enterprise boundaries.

        Returns:
            Tuple of (is_off_topic: bool, reason: str)
        """
        if not text:
            return False, "Clean"

        normalized = text.lower().strip()

        # Check explicit violations
        for pattern in self.prohibited_patterns:
            match = pattern.search(normalized)
            if match:
                return True, f"Blocked off-topic category: '{match.group(0)}'"

        # Check if the query completely lacks enterprise context and looks like random entertainment
        words = re.findall(r"\b\w+\b", normalized)
        if len(words) >= 4:
            has_domain_term = any(term in normalized for term in ENTERPRISE_DOMAIN_KEYWORDS)
            # If query is long and has zero connection to any enterprise concepts, check heuristics
            if not has_domain_term:
                entertainment_indicators = [
                    "minecraft", "fortnite", "gaming", "playstation", "recipe for cake",
                    "cook spaghetti", "astrology", "horoscope", "gossip", "celebrity gossip"
                ]
                if any(ei in normalized for ei in entertainment_indicators):
                    return True, "Query falls outside enterprise business domain"

        return False, "In-scope enterprise query"


topic_guard = TopicGuard()
