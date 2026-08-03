## Summary

Add an asynchronous invoice-export workflow for large historical exports while
preserving the existing synchronous `GET /v1/invoices/export` endpoint.

## Requested change

- Add `POST /v1/invoice-export-jobs` to request an export by date range.
- Add an export worker that uses `InvoiceRepository` and `InvoiceExportService`.
- Write generated CSV files to a new GCS bucket with seven-day lifecycle rules.
- Add `GET /v1/invoice-export-jobs/{job_id}` returning status and a signed URL.
- Preserve the existing synchronous endpoint and CSV columns.

## Acceptance criteria

- Existing invoice API and synchronous-export contract tests remain unchanged.
- Integration tests cover job creation, worker completion, signed URLs, failure,
  retry, and lifecycle behavior.
- Infrastructure defines a queue, worker runtime, GCS bucket, IAM, and alerts.
- Estimated monthly POC cost is documented and expected to remain within
  `$50-$500/mo`.

## Expected POC classification

Medium risk, Medium FinOps cost (`$50-$500/mo`), and no breaking contract.
Human approval is not expected unless the agent identifies an unresolved
security or compatibility concern.
