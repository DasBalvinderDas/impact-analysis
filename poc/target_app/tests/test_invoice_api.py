"""Deterministic tests for the sample application's current contracts."""

from decimal import Decimal

from billing_service.api.invoices import export_invoices_response, get_invoice_response
from billing_service.clients.customer_client import CustomerClient
from billing_service.consumers.reporting_consumer import build_reporting_row
from billing_service.models.invoice import Invoice
from billing_service.repositories.invoice_repository import InvoiceRepository
from billing_service.services.invoice_export import InvoiceExportService
from billing_service.services.invoice_service import InvoiceService


def _repository() -> InvoiceRepository:
    """Build the deterministic invoice repository used by all tests.

    This method achieves the following in sequence:

    Step 1 - Creates a representative invoice with a legacy customer identifier.
    Step 2 - Adds the invoice to an in-memory repository.
    Step 3 - Returns the repository to the test that requested it.
    """
    return InvoiceRepository(
        [Invoice("inv-100", "cust-legacy-7", Decimal("125.50"), "USD")]
    )


def test_get_invoice_preserves_v1_legacy_customer_contract() -> None:
    """Verify the current v1 API response includes ``legacy_customer_id``.

    This method achieves the following in sequence:

    Step 1 - Builds the invoice service and invokes the API adapter.
    Step 2 - Verifies the request succeeds.
    Step 3 - Confirms the field required by reporting consumers is present.
    """
    service = InvoiceService(_repository(), CustomerClient())
    payload, status = get_invoice_response("inv-100", service)

    assert status == 200
    assert payload["legacy_customer_id"] == "cust-legacy-7"


def test_missing_invoice_returns_not_found() -> None:
    """Verify an unknown invoice produces the current 404 response.

    This method achieves the following in sequence:

    Step 1 - Builds an empty repository and invoice service.
    Step 2 - Requests an identifier that does not exist.
    Step 3 - Confirms the API returns the documented error and status.
    """
    service = InvoiceService(InvoiceRepository(), CustomerClient())

    assert get_invoice_response("missing", service) == ({"error": "invoice_not_found"}, 404)


def test_reporting_consumer_reads_legacy_customer_id() -> None:
    """Verify the upstream reporting consumer depends on the legacy field.

    This method achieves the following in sequence:

    Step 1 - Supplies a representative v1 API response to the consumer.
    Step 2 - Builds the downstream reporting row.
    Step 3 - Confirms the legacy identifier becomes the reporting key.
    """
    row = build_reporting_row(
        {
            "invoice_id": "inv-100",
            "legacy_customer_id": "cust-legacy-7",
            "amount": "125.50",
            "currency": "USD",
        }
    )

    assert row["customer_key"] == "cust-legacy-7"


def test_csv_export_uses_existing_columns() -> None:
    """Verify synchronous exports use the documented CSV layout.

    This method achieves the following in sequence:

    Step 1 - Creates the invoice export service.
    Step 2 - Requests the API-style CSV response.
    Step 3 - Confirms its status, content type, header, and data row.
    """
    body, status, content_type = export_invoices_response(InvoiceExportService(_repository()))

    assert status == 200
    assert content_type == "text/csv"
    assert body.splitlines() == [
        "invoice_id,legacy_customer_id,amount,currency",
        "inv-100,cust-legacy-7,125.50,USD",
    ]
