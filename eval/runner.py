"""Dataset loading and multi-variant evaluation orchestration."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from extractor import extract_invoice

from .scoring import aggregate, score_invoice

ROOT = Path(__file__).resolve().parents[1]


def load_dataset(labels_path: Path) -> list[dict[str, Any]]:
    rows = json.loads(labels_path.read_text(encoding="utf-8"))
    if not isinstance(rows, list) or not rows:
        raise ValueError("labels file must contain a non-empty JSON array")
    return rows


def run_variant(
    variant: str,
    mode: str,
    labels_path: Path,
    tolerance: float,
    include_details: bool = False,
) -> dict[str, Any]:
    rows = load_dataset(labels_path)
    data_root = labels_path.parents[1]
    document_scores = []
    details = []
    for row in rows:
        text = (data_root / row["document"]).read_text(encoding="utf-8")
        prediction = extract_invoice(text, variant=variant, mode=mode)
        score = score_invoice(prediction, row["expected"], tolerance)
        document_scores.append(score)
        if include_details:
            details.append({"id": row["id"], "prediction": prediction, "scores": score})
    result = {"variant": variant, "mode": mode, **aggregate(document_scores)}
    if include_details:
        result["details"] = details
    return result


def run_evaluation(
    variants: list[str],
    mode: str = "heuristic",
    labels_path: Path | None = None,
    tolerance: float = 0.01,
    include_details: bool = False,
) -> dict[str, Any]:
    labels_path = labels_path or ROOT / "data" / "labels" / "invoices.json"
    return {
        "dataset": labels_path.relative_to(ROOT).as_posix() if labels_path.is_relative_to(ROOT) else str(labels_path),
        "money_tolerance": tolerance,
        "mode": mode,
        "results": [
            run_variant(variant, mode, labels_path, tolerance, include_details)
            for variant in variants
        ],
    }
