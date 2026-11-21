# Onboarding and integration

The email-based onboarding and initial authenticated merchant APIs described in this document are now implemented in `backend/app/main.py`. The earlier prototype modules remain in the repository as legacy reference code and are not used by the active ASGI application.

## Implemented API contract

- `POST /api/v1/auth/register`: email, password, merchant profile and mandatory terms acceptance; sends an email verification code.
- `POST /api/v1/auth/verify-email`: validates a hashed, expiring, single-use six-digit code.
- `POST /api/v1/auth/resend-verification`: sends a new code subject to a cooldown.
- `POST /api/v1/auth/login`: email/password authentication; requires verified email and returns a short-lived bearer token.
- `POST /api/v1/auth/forgot-password` and `POST /api/v1/auth/reset-password`: single-use, expiring reset-token flow.
- `GET /api/v1/auth/me`: authenticated profile.
- `GET /api/v1/auth/me/export` and `DELETE /api/v1/auth/me`: data export and password-confirmed account deletion.
- `GET /api/v1/dashboard/summary`: business-scoped metrics and recent transactions.
- `POST /api/v1/voice/parse` and `POST /api/v1/voice/confirm`: review-first voice parsing and explicit transaction persistence.
- `GET /api/v1/customers`, `GET /api/v1/customers/{id}/transactions`, `GET/POST /api/v1/transactions`: business-scoped khata and ledger.
- `GET/POST /api/v1/invoices` and `GET /api/v1/invoices/{id}`: basic invoice records.
- `GET /api/v1/government-schemes`, `GET /categories`, `GET /sources`, and authenticated `POST /{id}/assess`: small official-portal catalogue and profile-completeness assessment.

## Configuration

The frontend uses the same origin as the API in production. For a separate frontend origin, set `window.BOLOKHATA_API_URL` before the page scripts load and configure the exact origin in `CORS_ORIGINS`.

SMTP delivery is configured using server-side `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, and `SMTP_FROM`. Set `PASSWORD_RESET_URL` to the deployed reset page. Never expose these values in frontend code.

## Important feature boundaries

- The voice parser is rule-based and can misread accents, names, amounts and transaction intent. A human must review and confirm every entry.
- Invoice records currently contain a single description and total. GST tax calculations, itemised lines, statutory invoice fields and PDF generation are not implemented.
- Scheme assessment currently checks profile completeness only. It is not an official eligibility decision or live government integration.
- Production rate limiting across multiple workers, monitoring, backup/restore and a security audit must be configured at the deployment layer.
- The legal pages are drafts and require operator/legal review before launch.

See [PRODUCTION_DEPLOYMENT.md](PRODUCTION_DEPLOYMENT.md) for deployment instructions and release gates.
