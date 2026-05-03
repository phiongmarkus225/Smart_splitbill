"""
Offline OCR extraction using EasyOCR.
Returns the same dict format as extractor.py — drop-in compatible.

Teaching note: This shows the difference between traditional OCR (raw text
extraction + rule-based parsing) vs. AI extraction (Gemini understands
structure and outputs JSON directly). The results here are best-effort.
"""

import io
import re
import time

import numpy as np
from PIL import Image

_reader = None


def _get_reader():
    """Lazy-load EasyOCR reader (downloads ~200 MB of models on first use)."""
    global _reader
    if _reader is None:
        import os
        import easyocr
        os.makedirs(os.path.expanduser("~/.EasyOCR/model"), exist_ok=True)
        _reader = easyocr.Reader(["en", "id"], gpu=False, verbose=False)
    return _reader


def extract_receipt_ocr(image_bytes: bytes, mime_type: str = "image/jpeg") -> dict:
    """Extract receipt using EasyOCR (offline, no API key needed).

    Returns the same shape as extract_receipt():
        data   — parsed receipt dict (best-effort)
        raw    — raw OCR text lines
        error  — error message or None
        time_s — elapsed seconds
    """
    start = time.time()
    try:
        reader = _get_reader()
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        img_array = np.array(image)
        results = reader.readtext(img_array, detail=1)
        raw_text = "\n".join(text for _, text, conf in results if conf > 0.3)
    except Exception as exc:
        return {"data": None, "raw": str(exc), "error": str(exc), "time_s": time.time() - start}

    elapsed = time.time() - start
    parsed = _parse_receipt_text(raw_text)
    return {"data": parsed, "raw": raw_text, "error": None, "time_s": elapsed}


# ─── Rule-based parser ────────────────────────────────────────────────────────

_EXTRA_KEYWORDS = re.compile(
    r"\b(tax|pajak|pb1|service|charge|disc|diskon|tip|gratuity|voucher|promo)\b",
    re.IGNORECASE,
)
_TOTAL_KEYWORDS = re.compile(
    r"\b(grand\s*total|total|jumlah|tagihan|bayar)\b",
    re.IGNORECASE,
)
_PRICE_PATTERN = re.compile(r"[\d.,]{3,}")


def _parse_idr(text: str) -> float:
    """Parse Indonesian-format numbers (25.000 → 25000, 1.250.000 → 1250000)."""
    cleaned = re.sub(r"\.(?=\d{3}(?:\D|$))", "", text)
    cleaned = cleaned.replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def _extract_amount(line: str) -> float | None:
    """Return the last price-like number found on a line, or None."""
    matches = _PRICE_PATTERN.findall(line)
    for candidate in reversed(matches):
        val = _parse_idr(candidate)
        if val >= 100:  # ignore tiny numbers (qty, table number, etc.)
            return val
    return None


def _strip_numbers(text: str) -> str:
    cleaned = re.sub(r"[\d.,]+", "", text).strip(" :-/|")
    return cleaned or text.strip()


def _parse_receipt_text(text: str) -> dict:
    lines = [l.strip() for l in text.splitlines() if l.strip()]

    merchant = "Unknown"
    items: list[dict] = []
    extras: list[dict] = []
    total: float | None = None

    # First non-empty, non-numeric line is likely the merchant name
    for line in lines[:5]:
        if not re.match(r"^[\d.,\s]+$", line):
            merchant = line
            break

    for line in lines:
        amount = _extract_amount(line)
        if amount is None:
            continue

        if _TOTAL_KEYWORDS.search(line):
            if total is None or amount > total:
                total = amount
        elif _EXTRA_KEYWORDS.search(line):
            label = _strip_numbers(line)
            extras.append({"label": label, "amount": amount})
        else:
            name = _strip_numbers(line)
            items.append({"name": name, "qty": 1, "unit_price": amount, "total": amount})

    items_sum = sum(i["total"] for i in items)
    extras_sum = sum(e["amount"] for e in extras)
    inferred_total = total or (items_sum + extras_sum)

    return {
        "merchant": merchant,
        "currency": "IDR",
        "items": items,
        "subtotal": items_sum,
        "extras": extras,
        "total": inferred_total,
    }
