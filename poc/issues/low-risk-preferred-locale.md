## Summary

Add an optional `preferred_locale` field to notification preferences so invoice
emails can be localized. Default existing and new users to `en-US`.

## Requested change

- Add nullable/additive `preferred_locale` to the `user_preferences` table with
  default `en-US`.
- Extend `UserPreferences` and `NotificationPreferencesService` to read the
  value.
- Do not change `GET /v1/invoices/{invoice_id}` or any other public API response.
- Do not add cloud resources or new services.

## Acceptance criteria

- Existing preference records behave as `en-US` after migration.
- Existing invoice API contract tests continue to pass unchanged.
- Unit tests cover explicit and default locale values.
- The migration is backward compatible and can be rolled back safely.

## Expected POC classification

Low risk, Low FinOps cost (`<$50/mo`), and no human approval required.
