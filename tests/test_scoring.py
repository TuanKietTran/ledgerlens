from eval.scoring import aggregate, exact_match, score_invoice, tolerance_match


def test_exact_match_normalizes_case_and_whitespace() -> None:
    assert exact_match("  Northstar   CLOUD LLC ", "northstar cloud llc")


def test_exact_match_rejects_different_values() -> None:
    assert not exact_match("INV-100", "INV-101")


def test_exact_match_handles_nested_line_items() -> None:
    actual = [{"description": " Cloud  hosting ", "amount": 10.0}]
    expected = [{"description": "cloud hosting", "amount": 10}]
    assert exact_match(actual, expected)


def test_tolerance_match_accepts_boundary() -> None:
    assert tolerance_match(100.01, 100.00, tolerance=0.01)


def test_tolerance_match_rejects_value_outside_tolerance() -> None:
    assert not tolerance_match(100.02, 100.00, tolerance=0.01)


def test_tolerance_match_rejects_missing_and_boolean_values() -> None:
    assert not tolerance_match(None, 10.0)
    assert not tolerance_match(True, 1.0)


def test_score_invoice_applies_tolerance_to_each_line_money_value() -> None:
    expected = {
        "vendor": "Acme", "invoice_number": "1", "date": "2025-01-01", "currency": "USD",
        "line_items": [{"description": "Service", "quantity": 2, "unit_price": 3.00, "amount": 6.00}],
        "total_amount": 6.00,
    }
    actual = {
        **expected,
        "line_items": [{"description": "Service", "quantity": 2, "unit_price": 3.009, "amount": 6.009}],
        "total_amount": 6.009,
    }
    scores = score_invoice(actual, expected, tolerance=0.01)
    assert not scores["line_items_exact"]
    assert scores["line_item_unit_prices_tolerance"]
    assert scores["line_item_amounts_tolerance"]
    assert scores["total_amount_tolerance"]


def test_money_array_requires_matching_item_count() -> None:
    expected = {"line_items": [{"description": "A", "quantity": 1, "unit_price": 1, "amount": 1}]}
    actual = {"line_items": []}
    scores = score_invoice(actual, expected)
    assert not scores["line_item_unit_prices_tolerance"]
    assert not scores["line_item_amounts_tolerance"]


def test_aggregate_computes_percentages_and_overall() -> None:
    prediction = {
        "vendor": "Acme", "invoice_number": "1", "date": "2025-01-01", "currency": "USD",
        "line_items": [{"description": "A", "quantity": 1, "unit_price": 2, "amount": 2}],
        "total_amount": 2,
    }
    summary = aggregate([score_invoice(prediction, prediction)])
    assert summary["documents"] == 1
    assert summary["overall_accuracy"] == 100.0
    assert set(summary["metrics"].values()) == {100.0}
