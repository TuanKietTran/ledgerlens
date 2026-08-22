# Prompt variants

`zero_shot.md` gives only the output contract. `schema_guided.md` adds layout,
normalization, and locale guidance. The evaluator uses these exact files in live
LLM mode. Offline mode mirrors the same distinction with a narrow baseline and a
schema-aware deterministic parser so comparisons remain reproducible without an
API key.
