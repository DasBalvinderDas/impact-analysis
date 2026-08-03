"""Customer service client used to resolve legacy customer records."""


class CustomerClient:
    """Resolve customer display names from legacy customer identifiers.

    This client achieves the following in sequence:

    Step 1 - Accepts the legacy identifier used by the invoice domain.
    Step 2 - Represents the downstream customer-service lookup boundary.
    Step 3 - Returns a deterministic display name for POC execution.
    """

    def get_display_name(self, legacy_customer_id: str) -> str:
        """Return a display name for a legacy customer identifier.

        This method achieves the following in sequence:

        Step 1 - Receives the invoice's ``legacy_customer_id`` value.
        Step 2 - Normalizes it for the simulated customer-service request.
        Step 3 - Returns the display value consumed by invoice services.
        """
        return f"Customer {legacy_customer_id.upper()}"
