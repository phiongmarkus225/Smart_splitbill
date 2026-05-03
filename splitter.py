"""
Split logic — pure functions, no Streamlit imports.
Implements the per-person formula from the deck:

  person_total = Σ (item_total / |consumers(item)|)  +  share_of_extras

  share_of_extras = (person_subtotal / total_subtotal) × Σ extras

Invariant: Σ person_total == bill.total
"""

from typing import Dict, List, Set


def compute_split(
    items: List[dict],
    extras: List[dict],
    bill_total: float,
    assignments: Dict[int, Set[str]],
    participants: List[str],
) -> Dict[str, dict]:
    """Compute per-person totals.

    Args:
        items: list of item dicts with at least 'total' and 'name'
        extras: list of extra dicts with 'label' and 'amount'
        bill_total: the grand total from the receipt
        assignments: mapping of item_index -> set of participant names
        participants: list of all participant names

    Returns:
        dict mapping participant name -> {
            'items_subtotal': float,
            'extras_share': float,
            'total': float,
            'items_detail': list of (item_name, share_amount)
        }
    """
    result = {
        name: {"items_subtotal": 0.0, "extras_share": 0.0, "total": 0.0, "items_detail": []}
        for name in participants
    }

    for idx, item in enumerate(items):
        item_total = item.get("total", 0) or 0
        consumers = assignments.get(idx, set())

        if not consumers:
            continue

        share = item_total / len(consumers)
        for person in consumers:
            if person in result:
                result[person]["items_subtotal"] += share
                result[person]["items_detail"].append((item.get("name", f"Item {idx+1}"), round(share, 2)))

    total_subtotal = sum(r["items_subtotal"] for r in result.values())
    total_extras = sum(e.get("amount", 0) or 0 for e in extras)

    for person in participants:
        person_sub = result[person]["items_subtotal"]
        if total_subtotal > 0 and person_sub > 0:
            result[person]["extras_share"] = (person_sub / total_subtotal) * total_extras
        else:
            result[person]["extras_share"] = 0.0

        result[person]["total"] = round(
            result[person]["items_subtotal"] + result[person]["extras_share"], 2
        )
        result[person]["items_subtotal"] = round(result[person]["items_subtotal"], 2)
        result[person]["extras_share"] = round(result[person]["extras_share"], 2)

    return result


def format_currency(value: float, currency: str = "IDR") -> str:
    """Format a number as currency string."""
    if currency.upper() == "IDR":
        return f"Rp {value:,.0f}"
    return f"{currency} {value:,.2f}"
