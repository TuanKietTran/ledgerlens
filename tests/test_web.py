from fastapi.testclient import TestClient

from eval.web import app

client = TestClient(app)


def test_invoice_index_lists_labeled_invoices() -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert "inv-001" in response.text
    assert "Northstar Cloud LLC" in response.text
    assert "37.78%" in response.text


def test_invoice_detail_shows_both_scored_prompt_results() -> None:
    response = client.get("/invoice/inv-006")

    assert response.status_code == 200
    assert "<th><code>zero_shot</code></th>" in response.text
    assert "<th><code>schema_guided</code></th>" in response.text
    assert "data-variant='zero_shot' class='result incorrect'" in response.text
    assert "data-variant='schema_guided' class='result correct'" in response.text
    assert "<span class='badge'>Correct</span>" in response.text
    assert "<span class='badge'>Incorrect</span>" in response.text
    assert "Alpine Analytics GmbH" in response.text
