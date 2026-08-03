"""Invoice domain model used by the sample API and services."""

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class Invoice:
    """Represent an invoice returned by the public v1 API.

    This model achieves the following in sequence:

    Step 1 - Stores the invoice identifier and legacy customer identifier.
    Step 2 - Stores the amount and ISO currency code used for billing.
    Step 3 - Exposes a stable domain object to the repository and service layers.
    """

    invoice_id: str
    legacy_customer_id: str
    amount: Decimal
    currency: str = "USD"
