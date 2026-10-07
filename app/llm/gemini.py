import logging
import time
from typing import List, Optional

from google import genai

from app.config import settings

logger = logging.getLogger(__name__)

FALLBACK_MODELS = [
    "gemini-3.1-flash-lite-preview",
    "gemini-3.1-flash-lite",
    "gemini-3-flash-preview",
    "gemini-flash-latest",
    settings.gemini_model_name,
]


class GeminiLLM:
    def __init__(self):
        if not settings.gemini_api_key:
            raise ValueError("GEMINI_API_KEY is not configured.")

        self.client = genai.Client(api_key=settings.gemini_api_key)
        self.models_pool: List[str] = []
        for m in FALLBACK_MODELS:
            if m and m not in self.models_pool:
                self.models_pool.append(m)

    @staticmethod
    def _is_daily_quota_error(error_text: str) -> bool:
        daily_quota_indicators = [
            "GenerateRequestsPerDayPerProject-FreeTier",
            "GenerateRequestsPerDayPerModel-FreeTier",
            "generate_content_free_tier_requests",
            "quotaValue': '20'",
            '"quotaValue": "20"',
        ]
        return any(indicator in error_text for indicator in daily_quota_indicators)

    def _call_with_fallback(self, prompt: str, max_retries: int = 3) -> str:
        last_error = None

        for model_name in self.models_pool:
            for attempt in range(max_retries):
                try:
                    response = self.client.models.generate_content(
                        model=model_name,
                        contents=prompt,
                    )
                    if response.text:
                        return response.text.strip()
                    return ""
                except Exception as exc:
                    last_error = exc
                    error_text = str(exc)

                    # Daily quota
                    if self._is_daily_quota_error(error_text):
                        logger.warning(f"Quota issue with model {model_name}; trying next fallback model...")
                        break

                    # 503 High demand spike or 404
                    if "503" in error_text or "404" in error_text:
                        logger.warning(
                            f"Model {model_name} unavailable ({error_text[:80]}). Switching to next fallback model..."
                        )
                        break

                    # 429 Rate limit - backoff
                    if "429" in error_text:
                        if attempt < max_retries - 1:
                            wait_s = 2 ** attempt
                            logger.info(f"Rate limited on {model_name}; waiting {wait_s}s...")
                            time.sleep(wait_s)
                            continue
                        break

                    # Other error
                    logger.warning(f"Error calling {model_name}: {exc}; trying fallback...")
                    break

        raise RuntimeError(f"All Gemini models exhausted. Last error: {last_error}")

    def generate(self, query: str, context: str, max_retries: int = 3) -> str:
        prompt = f"""You are an enterprise knowledge assistant.

Answer the user's question using ONLY the provided context.

Rules:
1. Use only information present in the context.
2. Do not invent or assume facts.
3. If the context does not contain enough information, say:
   "The provided documents do not contain enough information to answer this question."
4. Keep the answer concise and factual.
5. Cite supporting information using [Source N].
6. Do not provide information that is not supported by the context.

User question:
{query}

Retrieved context:
{context}

Answer:
"""
        return self._call_with_fallback(prompt, max_retries=max_retries)

    def generate_raw(self, prompt: str, max_retries: int = 3) -> str:
        return self._call_with_fallback(prompt, max_retries=max_retries)


llm = GeminiLLM()