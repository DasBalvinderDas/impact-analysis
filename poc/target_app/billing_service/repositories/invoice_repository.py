"""In-memory invoice repository used by the POC test application."""

from collections.abc import Iterable

from billing_service.models.invoice import Invoice


class InvoiceRepository:
    """Read invoices from an in-memory collection.

    This repository achieves the following in sequence:

    Step 1 - Accepts invoice records from the application bootstrap layer.
    Step 2 - Indexes those records by invoice identifier.
    Step 3 - Provides deterministic lookup and listing behavior to services.
    """

    def __init__(self, invoices: Iterable[Invoice] = ()) -> None:
        """Initialize the invoice repository.

        This method achieves the following in sequence:

        Step 1 - Receives zero or more invoice domain objects.
        Step 2 - Builds an identifier-to-invoice lookup dictionary.
        Step 3 - Retains the dictionary for later read operations.
        """
        self._invoices = {invoice.invoice_id: invoice for invoice in invoices}

    def get(self, invoice_id: str) -> Invoice | None:
        """Return an invoice by identifier when it exists.

        This method achieves the following in sequence:

        Step 1 - Accepts the public invoice identifier.
        Step 2 - Looks up the identifier in the repository index.
        Step 3 - Returns the invoice or ``None`` when it is absent.
        """
        return self._invoices.get(invoice_id)

    def list_all(self) -> list[Invoice]:
        """Return all invoices in stable identifier order.

        This method achieves the following in sequence:

        Step 1 - Reads every invoice from the repository index.
        Step 2 - Sorts the invoices by identifier for deterministic output.
        Step 3 - Returns the ordered list to the calling service.
        """
        return sorted(self._invoices.values(), key=lambda invoice: invoice.invoice_id)
