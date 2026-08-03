"""Invoice orchestration service used by the v1 API."""

from billing_service.clients.customer_client import CustomerClient
from billing_service.models.invoice import Invoice
from billing_service.repositories.invoice_repository import InvoiceRepository


class InvoiceService:
    """Load invoice data and enrich it with customer information.

    This service achieves the following in sequence:

    Step 1 - Reads invoices through the repository boundary.
    Step 2 - Resolves customer data through the downstream customer client.
    Step 3 - Produces the dictionary consumed by the public API adapter.
    """

    def __init__(self, repository: InvoiceRepository, customer_client: CustomerClient) -> None:
        """Initialize the service with its repository and downstream client.

        This method achieves the following in sequence:

        Step 1 - Receives the invoice repository dependency.
        Step 2 - Receives the customer-service client dependency.
        Step 3 - Retains both dependencies for invoice retrieval.
        """
        self._repository = repository
        self._customer_client = customer_client

    def get_invoice(self, invoice_id: str) -> dict | None:
        """Return an API-ready representation of one invoice.

        This method achieves the following in sequence:

        Step 1 - Loads the invoice from ``InvoiceRepository``.
        Step 2 - Returns ``None`` when the invoice does not exist.
        Step 3 - Resolves the customer name using ``legacy_customer_id``.
        Step 4 - Serializes the enriched invoice for the API layer.
        """
        invoice = self._repository.get(invoice_id)
        if invoice is None:
            return None
        customer_name = self._customer_client.get_display_name(invoice.legacy_customer_id)
        return self._serialize(invoice, customer_name)

    @staticmethod
    def _serialize(invoice: Invoice, customer_name: str) -> dict:
        """Serialize an invoice while preserving the v1 response contract.

        This method achieves the following in sequence:

        Step 1 - Reads identity, customer, amount, and currency fields.
        Step 2 - Converts the decimal amount to a JSON-compatible string.
        Step 3 - Returns the response containing ``legacy_customer_id``.
        """
        return {
            "invoice_id": invoice.invoice_id,
            "legacy_customer_id": invoice.legacy_customer_id,
            "customer_name": customer_name,
            "amount": str(invoice.amount),
            "currency": invoice.currency,
        }
