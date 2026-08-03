# Billing Service Architecture

The billing service owns invoice retrieval and synchronous invoice CSV export.
`GET /v1/invoices/{invoice_id}` flows through `billing_service/api/invoices.py`,
`InvoiceService`, and `InvoiceRepository` to the `invoices` table. `InvoiceService`
uses `CustomerClient` to resolve a display name using `legacy_customer_id`.

The reporting consumer in `billing_service/consumers/reporting_consumer.py` is an
upstream consumer of the invoice response and requires `legacy_customer_id` as
its `customer_key`. Removing or renaming that field is a breaking API contract
change and requires reporting-team migration, contract testing, and technical
lead approval.

Invoice CSV export is synchronous and is exposed through
`GET /v1/invoices/export`. Large historical exports would require an asynchronous
job, object storage, lifecycle rules, and a signed-download URL. That additive
change has a broader operational and FinOps impact but does not replace the
existing endpoint.

Notification preferences are internal to the billing application and stored in
`user_preferences`. Adding optional `preferred_locale` with default `en-US`
does not change invoice API responses and has no new infrastructure cost.
