# Zero-shot invoice extraction

Extract the invoice into one JSON object. Return JSON only, with these keys:
`vendor`, `invoice_number`, `date`, `currency`, `line_items`, and `total_amount`.
Each line item has `description`, `quantity`, `unit_price`, and `amount`.
Use ISO `YYYY-MM-DD` dates and ISO 4217 currency codes. Use numbers, not formatted
money strings. Use `null` for an unknown scalar and `[]` if no line items are found.
Do not calculate or invent missing values.
