# BoloKhaata onboarding and dashboard integration notes

This branch adds a responsive account onboarding experience, a data-driven dashboard shell, voice transcript review, and a government-scheme catalogue UI.

## Frontend entry points

- `frontend/auth.html`: registration, email verification, sign-in, password reset screens.
- `frontend/auth.js`: validation and API client.
- `frontend/dashboard.html`: authenticated overview; empty metrics are shown as unavailable rather than fabricated.
- `frontend/dashboard.js`: loads the signed-in user's profile and dashboard summary; browser speech recognition creates a review-only draft.
- `frontend/schems.html`: scheme catalogue; cards are rendered from the backend response and official HTTPS government portal links only.
- `frontend/schemes.js`: scheme discovery, filters, source registry and eligibility assessment requests.

Set `window.BOLOKHATA_API_URL` before loading the page if the API is not hosted at `http://127.0.0.1:8000`.

## Important backend work required before production

The existing backend does **not** yet implement the email-based flow requested in the product brief. The checked-in `backend/user.py` and `backend/auth_service.py` use phone-number registration and login; the user schema does not include an email field or email verification state. Therefore the new email form cannot successfully register, verify, sign in, or reset passwords until the backend is migrated and deployed with these endpoints:

- `POST /api/v1/auth/register` — accept email/password and business onboarding fields; create an inactive/unverified account; send a one-time verification link or code.
- `POST /api/v1/auth/verify-email` — validate a short-lived, single-use verification token/code and activate the account.
- `POST /api/v1/auth/resend-verification` — rate-limited resend.
- `POST /api/v1/auth/login` — email/password login; reject unverified accounts; issue secure session/JWT.
- `POST /api/v1/auth/forgot-password` and a token-protected reset endpoint — single-use, expiring reset tokens.
- `GET /api/v1/auth/me` — return the authenticated user's profile plus business display fields.

The current `backend/main.py` imports modules from an `app.core`, `app.models`, `app.routers`, and `app.services` package layout, while the repository tree currently contains a set of flat modules at `backend/` and does not contain that package tree. Reconcile the backend entry point and module layout before treating the API as runnable. Do not solve this by creating duplicate model layers.

## Required security and data model changes

- Add a unique, normalized email field, `email_verified_at`, and secure verification/reset token hashes with expiry and single-use semantics. Never store raw OTP/reset tokens.
- Use a modern password hashing configuration and a strong environment-provided JWT secret. Remove fallback production secrets.
- Rate-limit registration, login, OTP resend, OTP verification and password-reset endpoints. Avoid account enumeration in reset responses.
- Keep business profile fields optional where possible; do not require Aadhaar, PAN or bank data for account creation.
- Validate all business records against the authenticated user's business on the server.
- Restrict CORS to configured frontend origins; do not combine wildcard origins with credentialed requests.
- Configure HTTPS, secure cookie/session policy (or carefully managed bearer tokens), CSRF protection where cookie auth is used, and email delivery credentials in server-side environment variables.
- Add migrations and tests for unverified login rejection, expired/reused OTP rejection, duplicate email, reset-token reuse, tenant isolation and permission checks.

## Voice workflow limitation

The dashboard uses browser speech recognition to produce a transcript and calls the existing voice parse endpoint to display a draft. It intentionally does not save a financial transaction. The current parse route is not a complete voice-billing workflow and must be followed by a server-side draft/confirm endpoint that validates customer/product/price, calculates totals using Decimal, and writes invoice, ledger and stock updates in one database transaction only after explicit confirmation.

## Scheme catalogue limitation

The scheme page consumes the existing catalogue and assessment API. It does not invent match percentages or claim approval. Ensure the sync job stores verified source URLs, source timestamps, official application URLs and scheme status. Only official portal links should be used for application actions. Review the eligibility rules and the existing seed data before public launch; stale scheme information must be labelled.

## Run the frontend

Serve `frontend/` from the same origin as the API static mount or a local static server. The account screens require the backend contract above; the existing phone-based API is not compatible. Check the browser console and API logs during integration.
