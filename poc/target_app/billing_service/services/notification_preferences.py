"""Notification preference service targeted by the low-risk scenario."""

from billing_service.models.user_preferences import UserPreferences


class NotificationPreferencesService:
    """Provide default invoice-notification preferences.

    This service achieves the following in sequence:

    Step 1 - Accepts a customer identifier.
    Step 2 - Builds the existing notification-preference domain object.
    Step 3 - Returns preferences without changing an external API contract.
    """

    def get_preferences(self, customer_id: str) -> UserPreferences:
        """Return default notification preferences for one customer.

        This method achieves the following in sequence:

        Step 1 - Receives the customer identifier.
        Step 2 - Enables the existing invoice email preference.
        Step 3 - Returns the preference object to internal callers.
        """
        return UserPreferences(customer_id=customer_id, invoice_email_enabled=True)
