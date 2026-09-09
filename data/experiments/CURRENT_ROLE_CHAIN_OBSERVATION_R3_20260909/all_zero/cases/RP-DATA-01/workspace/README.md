# Invoice and payment reconciliation

Implement a standard-library-only CLI:

`python reconcile.py --invoices INVOICES.csv --payments PAYMENTS.csv --output OUTPUT_DIR`

Read UTF-8 CSV (optional BOM). Exact ordered headers are `invoice_id,currency,amount` and `payment_id,invoice_id,currency,amount`. IDs must be nonempty strings (whitespace-only is invalid) and currencies are USD/EUR/CNY. Invoice amounts cannot be negative; payment amounts may be negative for refunds. Amounts are finite decimal strings with at most four fractional digits. Round every accepted row to cents using decimal ROUND_HALF_UP before aggregation. Preserve IDs and never use binary floating point for money.

Invoice IDs and payment IDs are unique within their respective export types. An identical normalized row repeats no work and increments duplicate_rows. A repeated ID with differing normalized values is rejected as duplicate_id. For payments, normalize amount before comparing duplicate content. Payments require an accepted invoice and matching currency. Process invoice rows first, then payment rows, in source order.

Bad rows are quarantined and do not stop other valid rows. Apply these reasons in order: missing_fields (missing/extra/blank fields); invalid_currency; invalid_amount; duplicate_id; unknown_invoice; currency_mismatch. Nonfinite or overprecision values are invalid_amount. Exact duplicates skip later validation and count only as duplicates. Retain every rejected row's source kind (`invoices` or `payments`), 1-based CSV record number (header is record 1), and reason. CSV quoted fields are supported; record number counts logical records, not physical lines.

Create exactly three report files in OUTPUT_DIR:

- `reconciliation.csv`, header `invoice_id,currency,invoiced,paid,balance,status`, sorted by invoice ID. All money fields have exactly two decimal places. Paid is the sum of accepted distinct payment amounts; balance=invoiced-paid. Status is settled when balance=0, underpaid when positive, overpaid when negative. Include invoices without payments.
- `rejected.csv`, header `source,row,reason`, ordered by source processing order then record number.
- `summary.json`, with `currencies` mapping each present currency to `invoices` (count), `invoiced`, `paid`, `balance` (two-decimal strings), plus integer `rejected_rows` and `duplicate_rows` at the top level. Emit currency keys sorted.

Print the same summary JSON to stdout. Empty exports with valid headers succeed with empty CSV data, currencies={} and zero counts. Missing/unreadable files, malformed CSV structure or invalid headers are fatal: exit nonzero and preserve an existing output directory without partial overwrite. Outputs of successful repeated runs must be byte-identical. Publish the report set together using a staging directory; do not retain obsolete output files. Document CLI usage and add self-authored tests, especially decimal rounding, duplicate/conflict handling, and failure recovery.
