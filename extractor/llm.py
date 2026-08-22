"""Minimal OpenAI-compatible client; intentionally dependency-free."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


class LLMError(RuntimeError):
    """Raised when live extraction cannot return a valid response."""


def extract_with_llm(text: str, variant: str) -> dict[str, Any]:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise LLMError("OPENAI_API_KEY is not set")
    prompt_path = ROOT / "prompts" / f"{variant}.md"
    if not prompt_path.exists():
        raise LLMError(f"unknown prompt variant: {variant}")
    payload = {
        "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        "temperature": 0,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": prompt_path.read_text(encoding="utf-8")},
            {"role": "user", "content": text},
        ],
    }
    request = urllib.request.Request(
        os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/") + "/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            body = json.load(response)
        content = body["choices"][0]["message"]["content"]
        result = json.loads(content)
    except (urllib.error.URLError, KeyError, IndexError, json.JSONDecodeError) as exc:
        raise LLMError(f"LLM request failed: {exc}") from exc
    return _validate(result)


def _validate(result: Any) -> dict[str, Any]:
    fields = ("vendor", "invoice_number", "date", "currency", "line_items", "total_amount")
    if not isinstance(result, dict) or not set(fields).issubset(result):
        raise LLMError("LLM response does not match the invoice schema")
    if not isinstance(result["line_items"], list):
        raise LLMError("line_items must be an array")
    return {key: result[key] for key in fields}
