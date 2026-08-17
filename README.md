# ledgerlens

Invoice extraction with a human-in-the-loop review queue — and, more to the
point, the measurement that says whether it actually works.

**Status:** planned. Starts once [ledgerline](https://github.com/TuanKietTran/ledgerline) ships.

## Scope of this repo

The feature itself — upload, extraction, review UI — is built inside
[ledgerline](https://github.com/TuanKietTran/ledgerline), because an LLM feature
that lives outside the product it serves proves nothing about integrating one.

**This repo holds the evaluation harness:** the labeled invoice set, the prompt
and schema versions, the scoring scripts, and the results. Kept separate because
the eval is the honest artifact, and it should be reproducible without standing
up the whole ERP.

## The problem

Most invoice-extraction demos show one PDF parsing correctly. That says nothing
about the cases that matter: multi-page invoices, VAT edge cases, layouts the
model has not seen, and totals that do not reconcile.

The interesting engineering question isn't extraction — it's what the system
does when it is **not confident**.

## Approach

```
Upload ──> text extraction (pdfplumber, Tesseract fallback)
            │
    LLM call (schema-constrained JSON) ──> validation (schema + arithmetic)
            │
   confidence ≥ threshold ──> auto-post draft invoice
   confidence <  threshold ──> review queue ──> human correction ──> few-shot store
```

Confidence is not the model's self-report alone. It combines schema validity,
whether line items actually sum to the stated total, a self-rated score, and
whether the vendor has been seen before.

**The arithmetic guard is the load-bearing part:** if line items don't sum to
the total, the result goes to review regardless of how confident the model
sounds.

## What gets measured

| Metric | Why it's here |
|---|---|
| Field-level accuracy | Per-field, not per-document — a document-level score hides which field fails |
| Category accuracy | Expense account assignment, the part a human would otherwise do |
| % auto-posted | The actual efficiency claim |
| Human-touch time saved | The only number a finance team cares about |

Plus a **before/after comparison** once the correction store holds ~30 examples,
to show whether corrections actually improve later runs or just accumulate.

## Honesty commitments

- A failure gallery ships with the results — the cases it gets wrong, and why.
- Synthetic invoices are labeled as synthetic, with layouts varied hard.
- Cost and latency per document are reported, not omitted.

## The design constraint

The ERP core treats posted invoices as immutable and enforces hard invariants.
A nondeterministic component has to live inside that without weakening it — so
extraction produces **drafts**, never posted entries, and a human confirms
anything the guards flag.
