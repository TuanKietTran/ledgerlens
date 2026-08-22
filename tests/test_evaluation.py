import json
from eval.runner import ROOT, run_evaluation
from extractor import extract_invoice


def test_labeled_set_has_twenty_distinct_readable_documents() -> None:
    rows = json.loads((ROOT / "data/labels/invoices.json").read_text(encoding="utf-8"))
    assert len(rows) == 20
    assert len({row["id"] for row in rows}) == 20
    assert all((ROOT / "data" / row["document"]).is_file() for row in rows)


def test_schema_guided_fallback_matches_the_labeled_set() -> None:
    rows = json.loads((ROOT / "data/labels/invoices.json").read_text(encoding="utf-8"))
    for row in rows:
        text = (ROOT / "data" / row["document"]).read_text(encoding="utf-8")
        assert extract_invoice(text, variant="schema_guided") == row["expected"]


def test_committed_baseline_headline_scores_are_reproducible() -> None:
    report = run_evaluation(["zero_shot", "schema_guided"])
    assert report["results"][0]["overall_accuracy"] == 37.77777777777778
    assert report["results"][1]["overall_accuracy"] == 100.0
