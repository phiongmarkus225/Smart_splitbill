"""
Gemini call + JSON parse + validation.
One concern: talk to the model, give back clean data.
"""

import json
import os
import re
import time

import google.generativeai as genai
from dotenv import load_dotenv

from prompts import RECEIPT_EXTRACTION_PROMPT

load_dotenv()

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

MODEL_NAME = "gemini-2.5-flash"


def extract_receipt(image_bytes: bytes, mime_type: str = "image/jpeg") -> dict:
    """Send an image to Gemini and return the parsed receipt dict.

    Returns a dict with keys:
        data   — the parsed receipt (or None on failure)
        raw    — the raw model response text
        error  — error message string (or None on success)
        time_s — inference time in seconds
    """
    model = genai.GenerativeModel(MODEL_NAME)

    image_part = {
        "mime_type": mime_type,
        "data": image_bytes,
    }

    start = time.time()
    try:
        response = model.generate_content(
            [RECEIPT_EXTRACTION_PROMPT, image_part],
            generation_config=genai.GenerationConfig(
                response_mime_type="application/json",
            ),
        )
        raw_text = response.text
    except Exception as exc:
        return {"data": None, "raw": str(exc), "error": str(exc), "time_s": time.time() - start}

    elapsed = time.time() - start

    parsed = _safe_parse(raw_text)
    if parsed is None:
        return {"data": None, "raw": raw_text, "error": "Could not parse JSON from model response.", "time_s": elapsed}

    return {"data": parsed, "raw": raw_text, "error": None, "time_s": elapsed}


def validate_totals(bill: dict, tolerance: float = 0.01) -> dict:
    """Check that sum(item.total) + sum(extras) ≈ bill.total.

    Returns dict with:
        valid        — bool
        items_sum    — float
        extras_sum   — float
        expected     — float (bill.total)
        diff         — float (absolute)
        diff_pct     — float (percentage)
    """
    items_sum = sum(item.get("total", 0) or 0 for item in bill.get("items", []))
    extras_sum = sum(extra.get("amount", 0) or 0 for extra in bill.get("extras", []))
    expected = bill.get("total", 0) or 0

    computed = items_sum + extras_sum
    diff = abs(computed - expected)
    diff_pct = (diff / expected) if expected else 0.0

    return {
        "valid": diff_pct <= tolerance,
        "items_sum": items_sum,
        "extras_sum": extras_sum,
        "expected": expected,
        "diff": diff,
        "diff_pct": diff_pct,
    }


def _safe_parse(text: str):
    """Try to parse JSON, stripping markdown fences if present."""
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        return json.loads(cleaned)
    except (json.JSONDecodeError, TypeError):
        return None
