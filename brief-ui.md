# Task: add a web UI to `ledgerlens`

Repo: C:\ledgerlens on this machine (already cloned, `origin` remote set, `main` branch,
existing invoice-extraction eval harness already implemented and pushed, 20 labeled
synthetic invoices, two prompt variants). This is a portfolio project for Kyle Tran's CV.
You are ADDING a UI to existing working code — do not break or remove the existing CLI,
extractor, eval harness, or tests.

## Why

The project currently only has a CLI eval harness. It needs a small real web UI so the
extraction-vs-ground-truth comparison can be demoed visually instead of only showing
terminal output.

## Scope

1. A minimal FastAPI (preferred) or Flask app in `eval/web.py` (or similar), exposing:
   - `GET /` — a list of the 20 labeled invoices (id + vendor name is enough) linking to
     a detail view each.
   - `GET /invoice/{id}` — a page showing, for that invoice:
     a. the raw invoice text,
     b. a side-by-side table of ground-truth fields vs. extracted fields for BOTH prompt
        variants (zero-shot and schema-guided), with each field visually marked
        correct/incorrect (color, not just text) based on the real scoring logic already
        implemented (exact-match / tolerance-match) — reuse those functions, don't
        re-implement scoring in the UI layer.
   - `GET /compare` (or on the home page) — the real overall accuracy comparison table
     across prompt variants, read from the existing results artifact
     (`results/latest.json` or equivalent), not hardcoded.
2. Add a script entry (e.g. `ledgerlens-web = "eval.web:main"` in `[project.scripts]`,
   using `uvicorn`) so it can be run with `uv run ledgerlens-web`. Add `fastapi` and
   `uvicorn` to `[project.dependencies]` (currently empty — that's fine, add them).
3. Default port: **8802** (avoid 3000, 8000, 8069, 8080, 8801, 9000-9001, 9092).
4. Update `README.md`: add a "Web UI" section under Status — how to run it
   (`uv run ledgerlens-web`, then open `http://localhost:8802`), a one-line description,
   and note a local UI now exists (still no public endpoint — handled separately).
5. Keep `uv run eval` (the existing CLI) working exactly as before — the web app should
   reuse the same extractor/scoring modules, not duplicate logic.
6. A couple of tests for the new route(s) (FastAPI TestClient) — `/` returns 200, and
   `/invoice/<a real id>` returns 200 and contains both prompt variants' results.

## Constraints

- Real, runnable code. The per-field correctness shown in the UI must come from the real
  scoring functions already in the repo — no fabricated/hardcoded correctness.
- Commit incrementally with clear messages. **Do not add any AI/assistant co-author
  trailers to commit messages** (no `Co-Authored-By`, no mention of AI tools) — plain
  conventional commits only.
- When finished (existing + new tests pass, `uv run ledgerlens-web` demonstrably serves a
  working page for a real invoice), `git push` to `origin main`.
- At the very end, print a single line to stdout starting with `LEDGERLENS_UI_DONE:`
  followed by a one-paragraph summary and the port/URL to reach it.

Work directory is the repo root. Go.
