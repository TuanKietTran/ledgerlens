"""Small local web UI for browsing invoice extraction evaluations."""

from __future__ import annotations

import json
from html import escape
from pathlib import Path
from typing import Any
from urllib.parse import quote

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse

from extractor import extract_invoice

from .runner import ROOT, load_dataset
from .scoring import score_invoice

LABELS_PATH = ROOT / "data" / "labels" / "invoices.json"
RESULTS_PATH = ROOT / "results" / "latest.json"
VARIANTS = ("zero_shot", "schema_guided")

FIELD_ROWS = (
    ("Vendor", "vendor", "vendor_exact", "exact"),
    ("Invoice number", "invoice_number", "invoice_number_exact", "exact"),
    ("Date", "date", "date_exact", "exact"),
    ("Currency", "currency", "currency_exact", "exact"),
    ("Line descriptions", "description", "line_item_descriptions_exact", "exact"),
    ("Line quantities", "quantity", "line_item_quantities_exact", "exact"),
    ("Line unit prices", "unit_price", "line_item_unit_prices_tolerance", "tolerance"),
    ("Line amounts", "amount", "line_item_amounts_tolerance", "tolerance"),
    ("Total amount", "total_amount", "total_amount_tolerance", "tolerance"),
)

app = FastAPI(title="ledgerlens", docs_url=None, redoc_url=None)

_STYLES = """
:root { color-scheme: light; --ink: #172033; --muted: #667085; --line: #d8dee9;
  --panel: #fff; --bg: #f4f7fb; --good: #e8f7ee; --good-ink: #18713c;
  --bad: #fff0f0; --bad-ink: #a12b2b; --accent: #3157c8; }
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--ink); font: 15px/1.5 system-ui, sans-serif; }
main { width: min(1180px, calc(100% - 32px)); margin: 0 auto; padding: 36px 0 64px; }
header { display: flex; align-items: baseline; justify-content: space-between; gap: 20px; margin-bottom: 24px; }
h1, h2 { line-height: 1.2; margin: 0 0 12px; } h1 { font-size: 30px; } h2 { margin-top: 30px; font-size: 20px; }
a { color: var(--accent); } nav a { margin-left: 16px; }
.subtle, .rule { color: var(--muted); } .rule { display: block; font-size: 12px; }
.panel { overflow: hidden; background: var(--panel); border: 1px solid var(--line); border-radius: 12px;
  box-shadow: 0 5px 18px rgba(26, 42, 73, .06); }
table { width: 100%; border-collapse: collapse; } th, td { padding: 12px 14px; border-bottom: 1px solid var(--line);
  text-align: left; vertical-align: top; } tr:last-child td { border-bottom: 0; }
th { background: #edf1f8; font-size: 13px; } .number { text-align: right; font-variant-numeric: tabular-nums; }
.invoice-list { display: grid; grid-template-columns: repeat(auto-fit, minmax(270px, 1fr)); gap: 12px; }
.invoice-list a { display: block; padding: 14px 16px; background: var(--panel); border: 1px solid var(--line);
  border-radius: 9px; text-decoration: none; } .invoice-list a:hover { border-color: var(--accent); }
.invoice-id { display: block; color: var(--muted); font-size: 12px; text-transform: uppercase; letter-spacing: .06em; }
pre { margin: 0; padding: 18px; overflow-x: auto; white-space: pre-wrap; word-break: break-word;
  background: #101827; color: #e6edf8; border-radius: 12px; }
td.result { border-left: 4px solid transparent; min-width: 190px; }
td.correct { background: var(--good); border-left-color: #38a169; }
td.incorrect { background: var(--bad); border-left-color: #d64545; }
.badge { display: inline-block; margin-top: 7px; padding: 2px 7px; border-radius: 999px; font-size: 11px; font-weight: 700; }
.correct .badge { color: var(--good-ink); background: #c9efd8; } .incorrect .badge { color: var(--bad-ink); background: #ffd5d5; }
.value { white-space: pre-wrap; word-break: break-word; font-family: ui-monospace, monospace; font-size: 13px; }
@media (max-width: 760px) { main { width: min(100% - 20px, 1180px); padding-top: 22px; }
  header { display: block; } nav a { margin: 0 16px 0 0; } .comparison { overflow-x: auto; } th, td { padding: 10px; } }
"""


def _page(title: str, content: str) -> HTMLResponse:
    return HTMLResponse(
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width, initial-scale=1'>"
        f"<title>{escape(title)} · ledgerlens</title><style>{_STYLES}</style></head>"
        "<body><main><header><div><h1>ledgerlens</h1>"
        "<div class='subtle'>Invoice extraction evaluation browser</div></div>"
        "<nav><a href='/'>Invoices</a><a href='/compare'>Comparison</a></nav></header>"
        f"{content}</main></body></html>"
    )


def _load_report() -> dict[str, Any]:
    try:
        report = json.loads(RESULTS_PATH.read_text(encoding="utf-8"))
        if not isinstance(report.get("results"), list) or not report["results"]:
            raise ValueError("results must be a non-empty list")
        return report
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        raise HTTPException(status_code=500, detail=f"Could not load {RESULTS_PATH.name}: {exc}") from exc


def _comparison(report: dict[str, Any]) -> str:
    rows = "".join(
        "<tr>"
        f"<td><code>{escape(str(result['variant']))}</code></td>"
        f"<td>{escape(str(result['mode']))}</td>"
        f"<td class='number'>{int(result['documents'])}</td>"
        f"<td class='number'><strong>{float(result['overall_accuracy']):.2f}%</strong></td>"
        "</tr>"
        for result in report["results"]
    )
    return (
        "<div class='panel comparison'><table><thead><tr><th>Prompt variant</th><th>Mode</th>"
        "<th class='number'>Documents</th><th class='number'>Overall accuracy</th></tr></thead>"
        f"<tbody>{rows}</tbody></table></div>"
    )


def _find_invoice(invoice_id: str) -> dict[str, Any]:
    for row in load_dataset(LABELS_PATH):
        if row["id"] == invoice_id:
            return row
    raise HTTPException(status_code=404, detail="Invoice not found")


def _field_value(invoice: dict[str, Any], key: str) -> Any:
    if key in {"description", "quantity", "unit_price", "amount"}:
        items = invoice.get("line_items")
        if not isinstance(items, list):
            return None
        return [item.get(key) if isinstance(item, dict) else None for item in items]
    return invoice.get(key)


def _display(value: Any) -> str:
    if value is None:
        return "<span class='subtle'>missing</span>"
    if isinstance(value, (list, dict)):
        rendered = json.dumps(value, ensure_ascii=False)
    else:
        rendered = str(value)
    return f"<span class='value'>{escape(rendered)}</span>"


@app.get("/", response_class=HTMLResponse)
def invoice_index() -> HTMLResponse:
    rows = load_dataset(LABELS_PATH)
    links = "".join(
        f"<a href='/invoice/{quote(str(row['id']), safe='')}'><span class='invoice-id'>{escape(str(row['id']))}</span>"
        f"<strong>{escape(str(row['expected']['vendor']))}</strong></a>"
        for row in rows
    )
    report = _load_report()
    content = (
        "<h2>Latest prompt comparison</h2>"
        f"<p class='subtle'>Read from <code>results/latest.json</code>; money tolerance ±{float(report['money_tolerance']):g}.</p>"
        f"{_comparison(report)}<h2>Labeled invoices</h2><div class='invoice-list'>{links}</div>"
    )
    return _page("Invoices", content)


@app.get("/compare", response_class=HTMLResponse)
def compare() -> HTMLResponse:
    report = _load_report()
    content = (
        "<h2>Overall accuracy comparison</h2>"
        "<p class='subtle'>This summary is loaded from the existing evaluation artifact at "
        f"<code>results/latest.json</code> (money tolerance ±{float(report['money_tolerance']):g}).</p>"
        f"{_comparison(report)}"
    )
    return _page("Prompt comparison", content)


@app.get("/invoice/{invoice_id}", response_class=HTMLResponse)
def invoice_detail(invoice_id: str) -> HTMLResponse:
    row = _find_invoice(invoice_id)
    document_path = LABELS_PATH.parents[1] / row["document"]
    try:
        raw_text = document_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f"Could not read invoice: {exc}") from exc

    expected = row["expected"]
    tolerance = float(_load_report()["money_tolerance"])
    predictions = {variant: extract_invoice(raw_text, variant=variant, mode="heuristic") for variant in VARIANTS}
    scores = {variant: score_invoice(predictions[variant], expected, tolerance) for variant in VARIANTS}

    table_rows = []
    for label, key, metric, rule in FIELD_ROWS:
        rule_label = "exact match" if rule == "exact" else f"±{tolerance:g} tolerance"
        cells = [
            f"<td><strong>{escape(label)}</strong><span class='rule'>{escape(rule_label)}</span></td>",
            f"<td>{_display(_field_value(expected, key))}</td>",
        ]
        for variant in VARIANTS:
            correct = scores[variant][metric]
            css_class = "correct" if correct else "incorrect"
            status = "Correct" if correct else "Incorrect"
            cells.append(
                f"<td class='result {css_class}'>{_display(_field_value(predictions[variant], key))}"
                f"<br><span class='badge'>{status}</span></td>"
            )
        table_rows.append(f"<tr>{''.join(cells)}</tr>")

    content = (
        f"<h2>{escape(str(row['id']))} · {escape(str(expected['vendor']))}</h2>"
        "<p class='subtle'>Prompt outputs are produced by the local deterministic extractor and scored with "
        "<code>eval.scoring.score_invoice</code>.</p>"
        "<div class='panel comparison'><table><thead><tr><th>Field / rule</th><th>Ground truth</th>"
        "<th><code>zero_shot</code></th><th><code>schema_guided</code></th></tr></thead>"
        f"<tbody>{''.join(table_rows)}</tbody></table></div>"
        f"<h2>Raw invoice text</h2><pre>{escape(raw_text)}</pre>"
    )
    return _page(str(row["id"]), content)


def main() -> None:
    """Run the local development server on the project's reserved port."""
    uvicorn.run("eval.web:app", host="127.0.0.1", port=8802)


if __name__ == "__main__":
    main()
