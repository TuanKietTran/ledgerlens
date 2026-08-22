"""Deterministic fallback extractors for offline, reproducible evaluation."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

EMPTY_RESULT: dict[str, Any] = {
    "vendor": None,
    "invoice_number": None,
    "date": None,
    "currency": None,
    "line_items": [],
    "total_amount": None,
}


def parse_number(value: str) -> float:
    """Parse common US and European invoice number formats."""
    cleaned = re.sub(r"[^0-9,.-]", "", value.strip())
    if not cleaned:
        raise ValueError(f"not a number: {value!r}")
    if "," in cleaned and "." in cleaned:
        if cleaned.rfind(",") > cleaned.rfind("."):
            cleaned = cleaned.replace(".", "").replace(",", ".")
        else:
            cleaned = cleaned.replace(",", "")
    elif "," in cleaned:
        tail = cleaned.rsplit(",", 1)[1]
        cleaned = cleaned.replace(",", ".") if len(tail) == 2 else cleaned.replace(",", "")
    return float(cleaned)


def parse_date(value: str) -> str | None:
    value = value.strip()
    formats = (
        "%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%Y/%m/%d", "%Y.%m.%d",
        "%d-%m-%Y", "%d %b %Y", "%d %B %Y", "%b %d %Y", "%B %d %Y",
        "%b %d, %Y", "%B %d, %Y",
    )
    for date_format in formats:
        try:
            return datetime.strptime(value, date_format).date().isoformat()
        except ValueError:
            continue
    return None


def _match(text: str, pattern: str) -> str | None:
    match = re.search(pattern, text, flags=re.IGNORECASE | re.MULTILINE)
    return match.group(1).strip() if match else None


def _pipe_items(text: str) -> list[dict[str, Any]]:
    items = []
    for line in text.splitlines():
        parts = [part.strip() for part in line.split("|")]
        if len(parts) != 4 or parts[0].lower() == "description":
            continue
        try:
            items.append(_item(parts[0], parts[1], parts[2], parts[3]))
        except ValueError:
            continue
    return items


def _semicolon_items(text: str) -> list[dict[str, Any]]:
    items = []
    for line in text.splitlines():
        parts = [part.strip() for part in line.split(";")]
        if len(parts) != 4 or parts[0].lower() in {"item", "description"} or "=" in line:
            continue
        try:
            items.append(_item(parts[0], parts[1], parts[2], parts[3]))
        except ValueError:
            continue
    return items


def _keyed_items(text: str) -> list[dict[str, Any]]:
    pattern = re.compile(
        r"^desc=([^;\r\n]+);\s*qty=([^;\r\n]+);\s*unit=([^;\r\n]+);\s*amount=([^;\r\n]+)$",
        re.IGNORECASE | re.MULTILINE,
    )
    return [_item(*match.groups()) for match in pattern.finditer(text)]


def _equation_items(text: str) -> list[dict[str, Any]]:
    pattern = re.compile(r"^([^\s]+)\s*x\s*([^\s]+)\s*=\s*([^\s]+)\s*::\s*(.+)$", re.MULTILINE)
    return [_item(match[4], match[1], match[2], match[3]) for match in pattern.finditer(text)]


def _item(description: str, quantity: str, unit_price: str, amount: str) -> dict[str, Any]:
    return {
        "description": description.strip(),
        "quantity": parse_number(quantity),
        "unit_price": parse_number(unit_price),
        "amount": parse_number(amount),
    }


def _currency(text: str) -> str | None:
    explicit = _match(
        text,
        r"^(?:currency|settlement currency)\s*[:=]?\s*([A-Z]{3})\s*$",
    ) or _match(text, r"^(?:all amounts in|amounts shown in)\s+([A-Z]{3})\s*$")
    if explicit:
        return explicit.upper()
    for marker, code in (("C$", "CAD"), ("A$", "AUD"), ("€", "EUR"), ("£", "GBP"), ("¥", "JPY"), ("$", "USD")):
        if marker in text:
            return code
    return None


def basic_extract(text: str) -> dict[str, Any]:
    """Narrow baseline matching one conventional label and table layout."""
    result = dict(EMPTY_RESULT)
    result["vendor"] = _match(text, r"^Vendor:\s*(.+)$")
    result["invoice_number"] = _match(text, r"^Invoice #:\s*(.+)$")
    raw_date = _match(text, r"^Invoice Date:\s*(.+)$")
    result["date"] = parse_date(raw_date) if raw_date else None
    currency = _match(text, r"^Currency:\s*([A-Z]{3})\s*$")
    result["currency"] = currency.upper() if currency else None
    result["line_items"] = _pipe_items(text)
    raw_total = _match(text, r"^Total:\s*(.+)$")
    result["total_amount"] = parse_number(raw_total) if raw_total else None
    return result


def schema_guided_extract(text: str) -> dict[str, Any]:
    """Schema-aware fallback supporting all documented synthetic layouts."""
    result = dict(EMPTY_RESULT)
    result["vendor"] = _match(
        text,
        r"^(?:Supplier Name|Supplier|Bill From|From|Vendor name|Vendor)\s*[:=]\s*(.+)$",
    )
    result["invoice_number"] = _match(
        text,
        r"^(?:Invoice Number|Invoice reference|Invoice No|Invoice #|Inv #|Reference|Document ID)\s*[:=]?\s*(.+)$",
    )
    raw_date = _match(
        text,
        r"^(?:Invoice Date|Issue Date|Billing date|Document date|Issued|Dated|Date)\s*[:=]\s*(.+)$",
    )
    result["date"] = parse_date(raw_date) if raw_date else None
    result["currency"] = _currency(text)
    result["line_items"] = (
        _pipe_items(text) + _semicolon_items(text) + _keyed_items(text) + _equation_items(text)
    )
    raw_total = _match(
        text,
        r"^(?:Amount Due|Grand Total|Balance Due|Invoice Total|TOTAL DUE|PAYABLE|Total)\s*[:=]?\s*(.+)$",
    )
    result["total_amount"] = parse_number(raw_total) if raw_total else None
    return result


def extract(text: str, variant: str) -> dict[str, Any]:
    if variant == "zero_shot":
        return basic_extract(text)
    if variant == "schema_guided":
        return schema_guided_extract(text)
    raise ValueError(f"unknown prompt variant: {variant}")
