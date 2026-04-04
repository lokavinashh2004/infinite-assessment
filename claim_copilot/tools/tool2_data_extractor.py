"""
tool2_data_extractor.py — Tool 2: Structured claim data extraction via Groq AI.

Sends raw document text to the Groq API with a strict extraction
prompt and parses the JSON response into an ExtractedClaim Pydantic model.
"""

from __future__ import annotations

import json
import re

from groq import Groq

from claim_copilot.config import GROQ_API_KEY, GROQ_MODEL
from claim_copilot.models.schemas import ExtractedClaim

# Initialise the Groq client once at module level (no global mutable state).
_client = Groq(api_key=GROQ_API_KEY)

# ─── Extraction prompt ─────────────────────────────────────────────────────────

_EXTRACTION_SYSTEM_PROMPT = """\
You are a medical insurance claim data extraction specialist.
Your sole job is to parse claim documents and return structured JSON.
You MUST return raw JSON only — no markdown, no code fences, no explanation.
If a field cannot be found in the document, use null for optional fields or
sensible defaults (empty list for arrays, 0.0 for amounts).
"""

_EXTRACTION_USER_TEMPLATE = """\
Extract ALL of the following fields from the medical claim document below.

Return a single flat JSON object with EXACTLY these keys:
- policy_id          (string)
- patient_name       (string)
- patient_age        (integer)
- hospital_name      (string)
- admission_date     (string, format YYYY-MM-DD)
- discharge_date     (string, format YYYY-MM-DD)
- diagnosis          (array of strings)
- treatment          (array of strings)
- total_amount       (float, amount in INR)
- itemized_costs     (array of objects, each with keys "item" (string) and "cost" (float))
- doctor_name        (string)
- claim_type         (string, MUST be one of: "inpatient", "outpatient", "daycare")

Rules:
1. Do NOT wrap the JSON in markdown or code blocks.
2. Do NOT include any text before or after the JSON.
3. All dates must be in ISO format YYYY-MM-DD.
4. claim_type must be exactly one of the three allowed values.
5. total_amount and all costs must be numeric floats, not strings.

CLAIM DOCUMENT:
---
{raw_text}
---
"""


def _strip_markdown_fences(text: str) -> str:
    """
    Remove markdown code fences (``` or ```json) from a string.

    Groq occasionally wraps JSON in fences despite instructions.

    Args:
        text: Raw string from Groq API response.

    Returns:
        Cleaned string with fences removed.
    """
    # Remove opening fence: ```json or ```
    text = re.sub(r"^```(?:json)?\s*\n?", "", text.strip(), flags=re.IGNORECASE)
    # Remove closing fence
    text = re.sub(r"\n?```\s*$", "", text.strip())
    return text.strip()


def extract_claim_data(raw_text: str) -> ExtractedClaim:
    """
    Send raw claim document text to Groq and parse the structured response.

    Args:
        raw_text: Plain text extracted from the claim document by Tool 1.

    Returns:
        ExtractedClaim Pydantic model populated with the extracted fields.

    Raises:
        ValueError: If Groq returns an unparseable response or validation fails.
        Exception: On Groq API failures (propagated as-is for the
            caller to handle or log).
    """
    if not raw_text or not raw_text.strip():
        raise ValueError("raw_text must not be empty; Tool 1 should have validated this.")

    prompt = _EXTRACTION_USER_TEMPLATE.format(raw_text=raw_text)

    try:
        chat_completion = _client.chat.completions.create(
            model=GROQ_MODEL,
            max_tokens=2048,
            messages=[
                {"role": "system", "content": _EXTRACTION_SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
        )
    except Exception as exc:
        raise RuntimeError(f"Groq API call failed during claim extraction: {exc}") from exc

    raw_response: str = chat_completion.choices[0].message.content or ""

    # Strip possible markdown fences before JSON parsing
    cleaned = _strip_markdown_fences(raw_response)

    try:
        data: dict = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Groq returned invalid JSON. "
            f"Parse error: {exc}. Raw response (first 500 chars): {raw_response[:500]!r}"
        ) from exc

    try:
        claim = ExtractedClaim(**data)
    except Exception as exc:
        raise ValueError(
            f"Extracted data failed Pydantic validation: {exc}. "
            f"Parsed dict: {data}"
        ) from exc

    return claim
