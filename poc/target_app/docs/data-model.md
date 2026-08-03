# Billing Data Model

`invoices` stores `invoice_id`, required `legacy_customer_id`, monetary amount,
currency, and creation time. An index supports lookups by
`legacy_customer_id`. A migration to `customer_ref` affects the database,
repository, domain model, API serialization, CSV exports, tests, and reporting
consumer.

`user_preferences` stores `customer_id`, `invoice_email_enabled`, and update
time. The low-risk POC proposes a nullable/additive `preferred_locale` column
with default `en-US`; existing records and invoice APIs remain compatible.
