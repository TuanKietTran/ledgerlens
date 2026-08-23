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
    assert "zero_shot" in response.text
    assert "schema_guided" in response.text
    assert "Incorrect" in response.text
    assert "Correct" in response.text
    assert "Alpine Analytics GmbH" in response.text
