"""Notification preference model for the low-risk POC scenario."""

from dataclasses import dataclass


@dataclass(frozen=True)
class UserPreferences:
    """Represent a customer's current notification preferences.

    This model achieves the following in sequence:

    Step 1 - Stores the customer identifier used by notifications.
    Step 2 - Stores whether invoice email notifications are enabled.
    Step 3 - Provides the object that the low-risk locale change will extend.
    """

    customer_id: str
    invoice_email_enabled: bool = True
