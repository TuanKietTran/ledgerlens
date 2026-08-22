# Labeled set

This directory contains 20 synthetic invoices. `invoices/*.txt` is the raw input
and `labels/invoices.json` is a JSON array containing each relative document path
and its `expected` object. The expected schema is:

```json
{
  "vendor": "string",
  "invoice_number": "string",
  "date": "YYYY-MM-DD",
  "currency": "ISO 4217 code",
  "line_items": [
    {"description": "string", "quantity": 1, "unit_price": 10.0, "amount": 10.0}
  ],
  "total_amount": 10.0
}
```

The set deliberately varies labels, date formats, currency notation, decimal
separators, and line-item layouts. All names and transactions are fictional.
