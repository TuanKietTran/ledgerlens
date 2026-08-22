"""Field-level exact and money-tolerance scoring."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from decimal import Decimal, InvalidOperation
from typing import Any

CORE_METRICS = (
    "vendor_exact",
    "invoice_number_exact",
    "date_exact",
    "currency_exact",
    "line_item_descriptions_exact",
    "line_item_quantities_exact",
    "line_item_unit_prices_tolerance",
    "line_item_amounts_tolerance",
    "total_amount_tolerance",
)

METRIC_LABELS = {
    "vendor_exact": "vendor (exact)",
    "invoice_number_exact": "invoice number (exact)",
    "date_exact": "date (exact)",
    "currency_exact": "currency (exact)",
    "line_items_exact": "line items (whole-array exact)",
    "line_item_descriptions_exact": "line descriptions (exact)",
    "line_item_quantities_exact": "line quantities (exact)",
    "line_item_unit_prices_exact": "line unit prices (exact)",
    "line_item_unit_prices_tolerance": "line unit prices (+/- tolerance)",
    "line_item_amounts_exact": "line amounts (exact)",
    "line_item_amounts_tolerance": "line amounts (+/- tolerance)",
    "total_amount_exact": "total amount (exact)",
    "total_amount_tolerance": "total amount (+/- tolerance)",
}


def _normalize(value: Any) -> Any:
    if isinstance(value, str):
        return " ".join(value.split()).casefold()
    if isinstance(value, Mapping):
        return {key: _normalize(item) for key, item in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return [_normalize(item) for item in value]
    return value


def exact_match(actual: Any, expected: Any) -> bool:
    """Compare values after case-folding strings and collapsing whitespace."""
    return _normalize(actual) == _normalize(expected)


def tolerance_match(actual: Any, expected: Any, tolerance: float = 0.01) -> bool:
    """Compare numeric money values using an inclusive absolute tolerance."""
    if isinstance(actual, bool) or isinstance(expected, bool):
        return False
    try:
        difference = abs(Decimal(str(actual)) - Decimal(str(expected)))
        return difference <= Decimal(str(tolerance))
    except (InvalidOperation, TypeError, ValueError):
        return False


def _item_values(items: Any, key: str) -> list[Any] | None:
    if not isinstance(items, list) or any(not isinstance(item, dict) or key not in item for item in items):
        return None
    return [item[key] for item in items]


def _money_array_match(actual: Any, expected: Any, key: str, tolerance: float) -> bool:
    actual_values = _item_values(actual, key)
    expected_values = _item_values(expected, key)
    if actual_values is None or expected_values is None or len(actual_values) != len(expected_values):
        return False
    return all(tolerance_match(a, e, tolerance) for a, e in zip(actual_values, expected_values, strict=True))


def score_invoice(actual: dict[str, Any], expected: dict[str, Any], tolerance: float = 0.01) -> dict[str, bool]:
    """Return every field-level score for one extracted invoice."""
    actual_items = actual.get("line_items")
    expected_items = expected.get("line_items")
    actual_descriptions = _item_values(actual_items, "description")
    expected_descriptions = _item_values(expected_items, "description")
    actual_quantities = _item_values(actual_items, "quantity")
    expected_quantities = _item_values(expected_items, "quantity")
    actual_prices = _item_values(actual_items, "unit_price")
    expected_prices = _item_values(expected_items, "unit_price")
    actual_amounts = _item_values(actual_items, "amount")
    expected_amounts = _item_values(expected_items, "amount")
    return {
        "vendor_exact": exact_match(actual.get("vendor"), expected.get("vendor")),
        "invoice_number_exact": exact_match(actual.get("invoice_number"), expected.get("invoice_number")),
        "date_exact": exact_match(actual.get("date"), expected.get("date")),
        "currency_exact": exact_match(actual.get("currency"), expected.get("currency")),
        "line_items_exact": exact_match(actual_items, expected_items),
        "line_item_descriptions_exact": exact_match(actual_descriptions, expected_descriptions),
        "line_item_quantities_exact": exact_match(actual_quantities, expected_quantities),
        "line_item_unit_prices_exact": exact_match(actual_prices, expected_prices),
        "line_item_unit_prices_tolerance": _money_array_match(actual_items, expected_items, "unit_price", tolerance),
        "line_item_amounts_exact": exact_match(actual_amounts, expected_amounts),
        "line_item_amounts_tolerance": _money_array_match(actual_items, expected_items, "amount", tolerance),
        "total_amount_exact": exact_match(actual.get("total_amount"), expected.get("total_amount")),
        "total_amount_tolerance": tolerance_match(actual.get("total_amount"), expected.get("total_amount"), tolerance),
    }


def aggregate(scores: list[dict[str, bool]]) -> dict[str, Any]:
    """Aggregate document scores into percentages and the canonical overall score."""
    if not scores:
        raise ValueError("cannot aggregate an empty evaluation")
    metrics = {
        key: 100 * sum(score[key] for score in scores) / len(scores)
        for key in scores[0]
    }
    overall = sum(metrics[key] for key in CORE_METRICS) / len(CORE_METRICS)
    return {"documents": len(scores), "overall_accuracy": overall, "metrics": metrics}
