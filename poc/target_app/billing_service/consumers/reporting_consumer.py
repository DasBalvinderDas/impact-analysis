"""Reporting consumer demonstrating a dependency on the v1 invoice contract."""


def build_reporting_row(invoice_payload: dict) -> dict:
    """Convert a v1 invoice payload into the reporting-service row shape.

    This method achieves the following in sequence:

    Step 1 - Reads ``invoice_id`` from the invoice API response.
    Step 2 - Reads the required ``legacy_customer_id`` contract field.
    Step 3 - Maps amount and currency into the reporting row.

    Removing ``legacy_customer_id`` is intentionally a breaking change for the
    high-risk POC scenario.
    """
    return {
        "invoice_key": invoice_payload["invoice_id"],
        "customer_key": invoice_payload["legacy_customer_id"],
        "gross_amount": invoice_payload["amount"],
        "currency": invoice_payload["currency"],
    }
