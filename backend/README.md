# BoloKhaata backend

The active API is the self-contained FastAPI application in `app/main.py`.

## Local development

From the repository root:

```powershell
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
cd backend
$env:APP_ENV = "development"
$env:DATABASE_URL = "sqlite:///./bolokhaata.sqlite3"
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000`. The API health endpoint is `/health`; interactive API docs are enabled only outside production.

In development, verification codes are printed to the backend terminal. Never run with `APP_ENV=development` in a public deployment.

## Production

Use PostgreSQL, HTTPS, a strong random `SECRET_KEY`, exact `CORS_ORIGINS` and `ALLOWED_HOSTS`, a real SMTP provider, and a public password-reset URL. Copy `.env.example` to `.env`, replace all placeholders, and follow [the deployment guide](../docs/PRODUCTION_DEPLOYMENT.md).

Production startup deliberately does not create or mutate tables. Run Alembic migrations before starting the API:

```bash
cd backend
alembic upgrade head
uvicorn main:app --host 0.0.0.0 --port 8000 --proxy-headers
```

## Tests

```bash
cd backend
pytest -q
```

The root-level Python modules are retained as legacy source from the earlier prototype and are not imported by the active application. Do not use the legacy SHA-256 password helper or the legacy phone-number auth modules. New routes and models belong in `app/main.py` until the application is split into separately tested modules.
