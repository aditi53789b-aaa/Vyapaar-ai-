# Production deployment and launch checklist

## Current implementation

The active FastAPI application is `backend/app/main.py`. It includes email/password registration, expiring one-time email verification codes, password reset, short-lived JWT access tokens, business-scoped customer/transaction/invoice data, dashboard summaries, voice-draft parsing and explicit transaction confirmation, official-portal scheme catalogue entries, profile-completeness assessment, personal-data export and account deletion.

The old flat modules under `backend/` are retained for reference only. They are legacy prototype code and are not imported by the active ASGI app. In particular, do not use the legacy SHA-256 password helper or phone-based auth modules.

## Deploy with Docker Compose

1. Install Docker Engine and the Docker Compose plugin on a server with a persistent disk.
2. Clone the repository and copy `.env.example` to `.env`.
3. Generate a strong secret with `python -c "import secrets; print(secrets.token_urlsafe(48))"`. Set a different long random password for PostgreSQL.
4. Replace every placeholder in `.env`: `SECRET_KEY`, database password, exact `CORS_ORIGINS`, `ALLOWED_HOSTS`, SMTP host/user/password/from address, and `PASSWORD_RESET_URL`.
5. Set `APP_ENV=production`. The API refuses to start if the secret, PostgreSQL, SMTP, reset URL or host configuration is unsafe or missing.
6. Run `docker compose up --build -d`. The API container applies Alembic migrations before starting Uvicorn.
7. Check `https://your-domain.example/health` through your HTTPS reverse proxy. The health response confirms database connectivity; it is not a substitute for end-to-end monitoring.

The Compose file exposes the API port. In production, place it behind a managed HTTPS load balancer or reverse proxy, restrict direct network access to the API container, and do not expose PostgreSQL's port publicly.

## Required infrastructure controls

- Terminate TLS at a trusted reverse proxy and enable HSTS only after HTTPS is correctly configured.
- Configure request-size limits and rate limits for registration, login, OTP verification/resend, password reset and voice endpoints. An example Nginx TLS and rate-limit configuration is in `deploy/nginx.conf`; replace the domain and certificate paths and validate it with `nginx -t` before enabling it. The account-level login lock and OTP cooldown in the API are defence-in-depth, not a replacement for a shared Redis/API-gateway limiter across multiple workers.
- Configure trusted proxy IPs and hostnames; do not trust arbitrary forwarded headers.
- Use a managed PostgreSQL service with encrypted storage, private networking, automated backups and tested point-in-time restore.
- Store secrets in the deployment platform's secret manager. Never commit `.env`, database files, SMTP credentials, reset tokens or customer exports.
- Configure structured logs, error reporting, uptime alerts, database connection monitoring and an incident-response contact.
- Run dependency and container vulnerability scans before each release; patch base images and pinned dependencies regularly.
- Configure email SPF, DKIM and DMARC for the sending domain and test delivery, bounce handling and abuse monitoring.
- Restrict CORS and `ALLOWED_HOSTS` to the actual production domains. Do not use wildcard origins.
- Verify the privacy, terms, retention, backup, deletion and grievance processes with the service operator and qualified counsel before inviting real merchants.

## Database migrations and backup

Migrations are in `backend/migrations`. Production startup intentionally does not call `create_all`; the container applies `alembic upgrade head`. Back up PostgreSQL before every migration and test restores periodically. Never use the prototype SQLite database as the production database.

Example backup from a trusted host with PostgreSQL client tools:

```bash
pg_dump --format=custom --no-owner --file=bolokhaata-backup.dump "$DATABASE_URL"
```

Store backups encrypted and separately from the application server. Define a retention schedule and verify that restore procedures work.

## Local tests

```bash
python -m venv .venv
# Activate the virtual environment, then:
pip install -r requirements.txt
cd backend
APP_ENV=test DATABASE_URL=sqlite:///./test.sqlite3 SECRET_KEY=ci-test-secret-key-not-for-production-0000000000 pytest -q
```

GitHub Actions runs Python compilation and the backend integration tests on pushes and pull requests.

## Feature boundaries that must be understood before launch

- Email delivery is implemented through SMTP configuration. The repository does not contain a real provider account or credentials; the operator must supply and test these.
- Speech capture depends on browser speech-recognition support. The transcript is a draft and must be reviewed. The parser is rule-based and may misinterpret Hindi, Hinglish, names, amounts or intent; do not auto-post without user confirmation.
- Invoice records currently store a single description and total, not a full itemised tax invoice with GST calculations, HSN/SAC, tax breakdown, seller legal details, payment reconciliation or PDF signing. Do not represent these invoices as GST-compliant tax invoices without further implementation and review.
- Scheme catalogue entries link to official programme portals. The current assessment checks whether basic profile fields are present; it does not implement authoritative scheme eligibility rules, live government integrations, application submission, loan approval or guarantee of benefits. Verify programme rules on the official portal.
- Terms and privacy pages in `frontend/terms.html` and `frontend/privacy.html` are publication drafts. The operator must replace the draft notices with reviewed policies, legal entity identity, grievance contact, actual processor list and retention schedule.
- No independent penetration test, external security audit, load test, disaster-recovery exercise or live SMTP delivery test has been performed in this repository workflow. CI tests are a baseline, not a production certification.

## Release gate

Do not announce the service as production-ready until the real deployment has been configured, migrations applied to a new PostgreSQL database, SMTP verified end-to-end, HTTPS and reverse-proxy rate limits tested, CI passing, legal notices approved, backup/restore tested, and a security review completed.
