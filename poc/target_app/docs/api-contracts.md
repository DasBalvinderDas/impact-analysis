# API Contracts

## GET /v1/invoices/{invoice_id}

The stable v1 response contains `invoice_id`, `legacy_customer_id`,
`customer_name`, `amount`, and `currency`. The reporting consumer requires
`legacy_customer_id`. Replacing it with `customer_ref` without a compatibility
window is a breaking change.

## GET /v1/invoices/export

The endpoint returns `text/csv` synchronously with columns `invoice_id`,
`legacy_customer_id`, `amount`, and `currency`. A future asynchronous export
endpoint must be additive and preserve this endpoint for existing callers.
