"""Invoice export service targeted by the medium-risk POC scenario."""

from billing_service.repositories.invoice_repository import InvoiceRepository


class InvoiceExportService:
    """Create a simple CSV export from invoice records.

    This service achieves the following in sequence:

    Step 1 - Loads invoice records through the repository layer.
    Step 2 - Converts each record into the existing CSV column layout.
    Step 3 - Returns the assembled export for synchronous download.
    """

    def __init__(self, repository: InvoiceRepository) -> None:
        """Initialize invoice exports with a repository.

        This method achieves the following in sequence:

        Step 1 - Receives the invoice repository dependency.
        Step 2 - Retains it as the source of export records.
        Step 3 - Makes the dependency available to ``export_csv``.
        """
        self._repository = repository

    def export_csv(self) -> str:
        """Render all invoices using the current synchronous CSV contract.

        This method achieves the following in sequence:

        Step 1 - Creates the CSV header with the legacy customer column.
        Step 2 - Reads invoices in deterministic order.
        Step 3 - Appends one row for each invoice and returns the CSV text.
        """
        rows = ["invoice_id,legacy_customer_id,amount,currency"]
        rows.extend(
            f"{item.invoice_id},{item.legacy_customer_id},{item.amount},{item.currency}"
            for item in self._repository.list_all()
        )
        return "\n".join(rows) + "\n"
