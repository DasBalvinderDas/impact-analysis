## Summary

Remove `legacy_customer_id` from `GET /v1/invoices/{invoice_id}` and replace it
with a new `customer_ref` field in a single release.

## Requested change

- Rename `invoices.legacy_customer_id` to `customer_ref` with no dual-write or
  compatibility window.
- Update `Invoice`, `InvoiceRepository`, `InvoiceService`, `CustomerClient`, the
  OpenAPI schema, and the CSV export column.
- Remove `legacy_customer_id` from the v1 JSON response immediately.
- Ask the reporting consumer to adopt `customer_ref` after deployment.

## Known dependencies

- `billing_service/consumers/reporting_consumer.py` reads
  `legacy_customer_id` as the required `customer_key`.
- `docs/api-contracts.md` declares the field stable in v1.
- `openapi.yaml`, `db/schema.sql`, CSV export, and tests explicitly reference
  `legacy_customer_id`.

## Acceptance criteria

- Database and code use `customer_ref` only.
- The existing `legacy_customer_id` field is removed from API and CSV output.
- Reporting is migrated and contract-tested.
- A rollback and consumer-coordination plan is approved before implementation.

## Expected POC classification

High risk because this is a breaking API/schema change with an upstream
consumer. `requires_human_approval` must be `true`; the agent must apply the
`impact:high-risk` label and mention `@tech-lead-review`.
