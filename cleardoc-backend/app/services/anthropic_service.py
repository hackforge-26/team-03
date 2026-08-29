import json
import time
import hashlib
from typing import Optional
from anthropic import AsyncAnthropic, RateLimitError, APIError
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)
from app.config import settings
from app.cache import cache_get, cache_set, make_document_cache_key
import structlog

logger = structlog.get_logger()
client = AsyncAnthropic(api_key=settings.anthropic_api_key)

SYSTEM_PROMPT = """
You are ClearDoc — a document simplification assistant that helps 
people who are confused by official documents. Your users include
elderly people, immigrants, low-income families, and people with
learning disabilities.

RULES:
1. Always respond with ONLY valid JSON — no extra text, no markdown
2. Simplify to 8th grade reading level maximum
3. Be warm, clear, and reassuring — the user is stressed
4. Never give legal or medical advice — explain what the document
   SAYS, not what the user should do legally
5. Always respond in the language specified in the request
6. Detect document type automatically from content
7. Extract ALL deadlines — they are critical

RESPONSE FORMAT (strict JSON, no deviation):
{
  "summary": "2-3 sentence plain English summary",
  "key_points": ["point 1", "point 2", "point 3"],
  "next_steps": ["step 1", "step 2", "step 3"],
  "urgency_flag": true or false,
  "urgency_message": "specific deadline info or null",
  "doc_type": "medical_bill|legal_notice|govt_form|landlord_letter|other",
  "detected_language": "en"
}
"""

COMPARE_PROMPT = """
You are a document analysis expert. Compare the provided document 
against standard templates for its document type.

Identify clauses that are:
- Unusual or non-standard (yellow flag)
- Potentially unfair or worth disputing (red flag)  
- Standard and normal (green — only flag if user might worry)

Respond ONLY in valid JSON:
{
  "flags": [
    {
      "clause": "exact clause or phrase from document",
      "severity": "red|yellow|green",
      "message": "plain English explanation of why this is flagged"
    }
  ],
  "all_clear": true or false
}
"""


@retry(
    retry=retry_if_exception_type((RateLimitError, APIError)),
    wait=wait_exponential(multiplier=1, min=1, max=8),
    stop=stop_after_attempt(3),
)
async def call_claude(
    text: str,
    language: str = "en",
    system_prompt: str = SYSTEM_PROMPT,
) -> dict:
    start = time.time()

    response = await client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1000,
        system=system_prompt,
        messages=[
            {
                "role": "user",
                "content": f"Language to respond in: {language}\n\nDocument:\n{text}",
            }
        ],
    )

    processing_time = int((time.time() - start) * 1000)
    raw = response.content[0].text.strip()

    # Strip markdown code fences if present
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]

    result = json.loads(raw)
    result["processing_time_ms"] = processing_time
    return result


async def explain_document(text: str, language: str = "en") -> tuple[dict, bool]:
    """
    Returns (result_dict, served_from_cache)
    Checks cache first — if hit, returns instantly without API call.
    """
    cache_key = make_document_cache_key(text + language)

    cached = await cache_get(cache_key)
    if cached:
        logger.info("cache_hit", key=cache_key)
        return cached, True

    logger.info("cache_miss_calling_anthropic")
    result = await call_claude(text, language)

    await cache_set(cache_key, result, ttl_seconds=86400)
    return result, False


async def get_followup_answer(
    original_text: str,
    question: str,
    language: str = "en",
) -> str:
    """
    Answers follow-up questions with full document context.
    """
    response = await client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=500,
        system=f"""You are ClearDoc. The user has a follow-up question
        about their document. Answer warmly in plain English at 8th grade
        level. Respond in language: {language}. Be specific to THEIR 
        document, not generic advice.""",
        messages=[
            {
                "role": "user",
                "content": f"Document:\n{original_text}\n\nQuestion: {question}",
            }
        ],
    )
    return response.content[0].text


async def compare_document(text: str) -> dict:
    """
    Compares document against standard templates.
    Flags unusual, unfair, or non-standard clauses.
    """
    return await call_claude(text, "en", COMPARE_PROMPT)
