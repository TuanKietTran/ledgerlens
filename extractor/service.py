"""Public routing API for the invoice extraction system under test."""

from __future__ import annotations

from typing import Any

from .heuristic import extract as heuristic_extract
from .llm import LLMError, extract_with_llm


def extract_invoice(text: str, variant: str = "schema_guided", mode: str = "heuristic") -> dict[str, Any]:
    """Extract an invoice using a live LLM, deterministic rules, or automatic fallback."""
    if mode == "heuristic":
        return heuristic_extract(text, variant)
    if mode == "llm":
        return extract_with_llm(text, variant)
    if mode == "auto":
        try:
            return extract_with_llm(text, variant)
        except LLMError:
            return heuristic_extract(text, variant)
    raise ValueError(f"unknown extraction mode: {mode}")
