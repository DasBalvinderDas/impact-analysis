"""Framework-neutral handlers for the public invoice API."""

from billing_service.services.invoice_export import InvoiceExportService
from billing_service.services.invoice_service import InvoiceService


def get_invoice_response(invoice_id: str, service: InvoiceService) -> tuple[dict, int]:
    """Build the HTTP-style response for ``GET /v1/invoices/{invoice_id}``.

    This method achieves the following in sequence:

    Step 1 - Passes the route identifier to ``InvoiceService``.
    Step 2 - Converts a missing invoice into a 404 response.
    Step 3 - Returns the v1 invoice representation with a 200 status.
    """
    invoice = service.get_invoice(invoice_id)
    if invoice is None:
        return {"error": "invoice_not_found"}, 404
    return invoice, 200


def export_invoices_response(service: InvoiceExportService) -> tuple[str, int, str]:
    """Build the HTTP-style response for ``GET /v1/invoices/export``.

    This method achieves the following in sequence:

    Step 1 - Requests a synchronous CSV export from the export service.
    Step 2 - Associates the payload with the ``text/csv`` content type.
    Step 3 - Returns the payload, successful status, and content type.
    """
    return service.export_csv(), 200, "text/csv"
