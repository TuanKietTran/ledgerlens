"""Command-line interface exposed as `uv run eval`."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .runner import ROOT, run_evaluation
from .scoring import METRIC_LABELS

DEFAULT_VARIANTS = ["zero_shot", "schema_guided"]


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Evaluate invoice extraction prompt variants")
    parser.add_argument("--mode", choices=("heuristic", "auto", "llm"), default="heuristic")
    parser.add_argument("--variants", nargs="+", default=DEFAULT_VARIANTS)
    parser.add_argument("--labels", type=Path, default=ROOT / "data" / "labels" / "invoices.json")
    parser.add_argument("--tolerance", type=float, default=0.01)
    parser.add_argument("--output", type=Path, default=ROOT / "results" / "latest.json")
    parser.add_argument("--details", action="store_true", help="include per-document predictions in JSON")
    return parser


def _table(headers: list[str], rows: list[list[str]]) -> str:
    widths = [max(len(header), *(len(row[index]) for row in rows)) for index, header in enumerate(headers)]
    separator = "-+-".join("-" * width for width in widths)
    lines = [" | ".join(header.ljust(widths[i]) for i, header in enumerate(headers)), separator]
    lines.extend(" | ".join(value.ljust(widths[i]) for i, value in enumerate(row)) for row in rows)
    return "\n".join(lines)


def print_report(report: dict[str, Any]) -> None:
    results = report["results"]
    comparison = [
        [result["variant"], result["mode"], str(result["documents"]), f'{result["overall_accuracy"]:.2f}%']
        for result in results
    ]
    print("Prompt comparison")
    print(_table(["Variant", "Mode", "Documents", "Overall"], comparison))
    print(f"\nPer-field accuracy (money tolerance: +/-{report['money_tolerance']:.2f})")
    metric_names = list(results[0]["metrics"])
    rows = [
        [METRIC_LABELS[name], *(f'{result["metrics"][name]:.2f}%' for result in results)]
        for name in metric_names
    ]
    print(_table(["Field / rule", *(result["variant"] for result in results)], rows))


def main() -> None:
    args = _parser().parse_args()
    if args.tolerance < 0:
        _parser().error("--tolerance must be non-negative")
    try:
        report = run_evaluation(
            variants=args.variants,
            mode=args.mode,
            labels_path=args.labels.resolve(),
            tolerance=args.tolerance,
            include_details=args.details,
        )
    except Exception as exc:  # CLI boundary: turn provider/data failures into a useful exit.
        print(f"evaluation failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print_report(report)
    print(f"\nJSON results: {args.output}")


if __name__ == "__main__":
    main()
