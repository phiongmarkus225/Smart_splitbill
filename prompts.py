"""
Prompt strings for Gemini receipt extraction.
Kept in one file so they are easy to iterate on.
"""

RECEIPT_EXTRACTION_PROMPT = """You are a receipt parser. Analyze the uploaded receipt image and extract all information into structured JSON.

Return ONLY valid JSON with this exact schema — no prose, no markdown fences, no explanation:

{
  "merchant": "string — the restaurant or store name",
  "currency": "string — e.g. IDR, USD, SGD",
  "items": [
    {
      "name": "string — item name as printed on the receipt",
      "qty": "integer — quantity purchased",
      "unit_price": "float — price per single unit",
      "total": "float — line total (qty × unit_price)"
    }
  ],
  "subtotal": "float — sum of all item totals before tax/service",
  "extras": [
    {
      "label": "string — use the original receipt label, e.g. 'PB1 10%', 'Service Charge 5%', 'Tax', etc.",
      "amount": "float — the charge amount"
    }
  ],
  "total": "float — grand total including all extras"
}

IMPORTANT RULES:
- If the receipt shows BOTH tax and service charge (common on Indonesian receipts as PB1 and SC), list them as SEPARATE entries in the extras array. Do NOT merge them.
- Use the original labels from the receipt for extras (e.g. "PB1 10%", "Service Charge 5%").
- All numeric values must be actual numbers, not strings.
- If a field is not visible on the receipt, use null.
- Do NOT invent items that are not on the receipt.
- Do NOT include markdown code fences in your response.
"""
