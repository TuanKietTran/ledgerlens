# ledgerlens

A reproducible evaluation harness for structured invoice extraction. It ships a
20-document synthetic labeled set, two prompt variants, field-level scoring, and
a self-contained reference extractor (the **system under test**).

> **Status:** local demo with a web UI; no public endpoint yet.

## Web UI

Browse all 20 labeled invoices, inspect ground truth against both prompt variants,
and view the latest overall accuracy comparison in a local web UI.

```bash
uv run ledgerlens-web
```

Then open [http://localhost:8802](http://localhost:8802). The UI is available
locally only; there is still no public endpoint.

## What is evaluated

Given plain invoice text, the extractor returns:

- vendor, invoice number, date, and ISO 4217 currency;
- ordered line items with description, quantity, unit price, and amount; and
- total amount.

The benchmark varies field labels, line-item layouts, date formats, currency
symbols, and US/European number separators. These are synthetic fixtures built
to test normalization and prompt instructions, not evidence of production OCR
or broad real-world generalization.

## System under test

[`extractor/`](extractor/) exposes one reference implementation with three modes:

- **`heuristic` (default):** deterministic and offline. `zero_shot` uses a narrow
  conventional-layout parser; `schema_guided` adds the same layout and locale
  guidance as the richer prompt. This makes every committed result reproducible.
- **`llm`:** sends the selected file from [`prompts/`](prompts/) to an
  OpenAI-compatible Chat Completions endpoint with JSON output enabled.
- **`auto`:** tries the LLM and falls back to the corresponding heuristic parser
  if credentials or the provider are unavailable.

For live mode, set `OPENAI_API_KEY`. `OPENAI_MODEL` defaults to `gpt-4o-mini`, and
`OPENAI_BASE_URL` defaults to `https://api.openai.com/v1`.

```bash
OPENAI_API_KEY=... uv run eval --mode llm
# Or exercise fallback behavior:
uv run eval --mode auto
```

Live results vary by model and provider and overwrite `results/latest.json`.
No invoice data is sent anywhere in the default heuristic mode.

## Labeled set format

[`data/invoices/`](data/invoices/) contains 20 raw UTF-8 text documents.
[`data/labels/invoices.json`](data/labels/invoices.json) is a JSON array of:

```json
{
  "id": "inv-001",
  "document": "invoices/inv-001.txt",
  "expected": {
    "vendor": "Northstar Cloud LLC",
    "invoice_number": "NS-1042",
    "date": "2025-01-15",
    "currency": "USD",
    "line_items": [
      {"description": "Cloud hosting", "quantity": 2, "unit_price": 125, "amount": 250}
    ],
    "total_amount": 250
  }
}
```

See [`data/README.md`](data/README.md) for the complete schema. All entities and
transactions are fictional.

## Run it

Python 3.12 and [uv](https://docs.astral.sh/uv/) are required.

```bash
uv sync --extra dev
uv run eval
uv run pytest
```

`uv run eval` compares both prompt variants in offline mode, prints a per-field
table, and writes the machine-readable report to
[`results/latest.json`](results/latest.json). Useful options include:

```bash
uv run eval --tolerance 0.01 --details
uv run eval --variants schema_guided --output results/schema-only.json
uv run eval --help
```

## Scoring

Text exact match is case-insensitive and collapses whitespace. Dates and
currencies are expected in canonical form. Line-item order and item count must
match. Money is reported both as exact match and with an inclusive absolute
`±0.01` tolerance.

The overall score is the unweighted mean of nine non-duplicated measures:
vendor, invoice number, date, currency, line descriptions, and quantities use
exact match; line unit prices, line amounts, and total use tolerance match. The
additional exact-money and whole-line-array rows are diagnostics and are not
counted twice.

## Reproducible baseline results

These numbers come from `uv run eval` in deterministic heuristic mode on all 20
fixtures:

| Prompt variant | Documents | Overall accuracy |
|---|---:|---:|
| `zero_shot` | 20 | **37.78%** |
| `schema_guided` | 20 | **100.00%** |

| Core field / rule | `zero_shot` | `schema_guided` |
|---|---:|---:|
| Vendor (exact) | 25.00% | 100.00% |
| Invoice number (exact) | 25.00% | 100.00% |
| Date (exact) | 25.00% | 100.00% |
| Currency (exact) | 40.00% | 100.00% |
| Line descriptions (exact) | 50.00% | 100.00% |
| Line quantities (exact) | 50.00% | 100.00% |
| Line unit prices (±0.01) | 50.00% | 100.00% |
| Line amounts (±0.01) | 50.00% | 100.00% |
| Total amount (±0.01) | 25.00% | 100.00% |

The gap is intentional: the zero-shot fallback represents a narrow baseline,
while the schema-guided variant encodes the layout and locale cases represented
in this labeled set. The committed JSON includes all diagnostic metrics so a
future prompt or model can be compared under the same scoring contract.
