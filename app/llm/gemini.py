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
        prompt = f"""You are an enterprise knowledge assistant with access to retrieved document excerpts.

Your task is to answer the user's question using the provided context below.

IMPORTANT RULES:
1. The context contains real excerpts from enterprise documents. Use them to answer the question.
2. Always cite the source(s) you used using the format [Source N] (e.g., [Source 1], [Source 2]).
3. If multiple sources are relevant, cite all of them.
4. Write a clear, factual, and concise answer based on what the context says.
5. Do NOT invent information that is not in the context.
6. ONLY say you cannot answer if the context is completely unrelated to the question — this should be rare.
   When in doubt, provide the best answer you can from the available context.
7. Do not repeat the question back. Go straight to the answer.

User question:
{query}

Retrieved context (from enterprise knowledge base):
{context}

Answer (with citations):
"""
        return self._call_with_fallback(prompt, max_retries=max_retries)

    def generate_raw(self, prompt: str, max_retries: int = 3) -> str:
        return self._call_with_fallback(prompt, max_retries=max_retries)


llm = GeminiLLM()