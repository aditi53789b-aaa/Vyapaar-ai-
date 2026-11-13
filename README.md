# Vyapaar-ai-
#  Vyaapaar AI – Your AI-Powered Digital Business Assistant

**Empowering Small Businesses, Street Vendors, and Micro-Entrepreneurs Through AI**

Vyaapaar AI is an AI-powered digital business management platform designed to simplify financial record-keeping for street vendors, small shop owners, local merchants, and independent entrepreneurs.

The platform enables users to manage their daily transactions, maintain customer credit records (*Udhar*), generate invoices, and understand their business performance using simple voice commands in their preferred language.

Our goal is to make digital business management accessible, affordable, and effortless for everyone — regardless of their technical knowledge or literacy level.

---

## The Problem

Millions of small business owners and street vendors still manage their businesses using traditional paper-based notebooks (*Khata*).

This creates several challenges:

- **Manual Record Keeping:** Maintaining daily sales and expenses manually is time-consuming.
- **Untracked Credit:** Tracking customer loans and pending payments (*Udhar*) becomes difficult.
- **Language Barriers:** Most digital accounting applications are not designed for users comfortable with regional languages.
- **Financial Accessibility:** Small merchants often lack organized financial records needed to demonstrate their business activity when applying for loans.
- **Limited Digital Literacy:** Complicated interfaces prevent many small business owners from adopting digital solutions.

## Our Solution

Vyaapaar AI transforms traditional business record-keeping into a simple, voice-driven digital experience.

Instead of manually entering every transaction, users can simply speak naturally.

**Example:**

> "Ramesh ko 2 kilo chawal 120 rupaye ka udhaar diya."

Vyaapaar AI processes the voice input, identifies the customer, item, quantity, amount, and credit status, and automatically updates the digital ledger.

Users can also generate invoices, monitor outstanding payments, and access AI-powered financial insights.

---

## Key Features

### 1. Voice-Based Transaction Management
- Add transactions using natural voice commands.
- Support for regional languages and multilingual interaction.
- Convert speech into structured transaction data.
- Automatically identify transaction details such as customer, product, quantity, and amount.
- Reduce the need for manual typing.

### 2. Smart Digital Khata
- Maintain digital customer-wise credit records.
- Track pending payments and outstanding balances.
- View transaction history.
- Add, update, and manage customer information.
- Replace traditional paper-based Khata registers.

### 3. Automated Invoice Generation
- Generate professional digital invoices.
- Automatically populate transaction details.
- Maintain invoice history.
- Export invoices for sharing and record-keeping.

### 4. AI-Powered Business Assistant
- Understand natural-language business queries.
- Retrieve relevant transaction information.
- Provide useful summaries of business activity.
- Help merchants understand their sales and pending payments.

### 5. Micro-Credit Readiness Copilot
An intelligent financial assistance feature that helps merchants organize their business records for potential loan applications.

- Analyze available transaction and ledger data.
- Generate structured financial summaries.
- Organize business transaction history.
- Provide guidance based on relevant government financial scheme guidelines, such as PM SVANidhi.
- Generate documentation-ready financial statements.

### 6. Multilingual and Accessible Interface
- Designed for users with limited digital literacy.
- Simple and intuitive interface.
- Voice-first interaction.
- Regional language support.

---

##  Technology Stack

| Layer | Technologies |
|---|---|
| Frontend | Next.js, React.js |
| Styling | Tailwind CSS, Shadcn UI |
| Backend | API-based backend architecture |
| Offline Storage | IndexedDB, Dexie.js |
| PWA | Workbox |
| Voice Recording | MediaRecorder API |
| Speech Recognition | Sarvam AI / Bhashini / Whisper |
| AI Integration | Gemini / LLM APIs |
| AI Workflow | LangChain.js / Vercel AI SDK |
| Invoice Generation | PDF generation tools |
| Framework | FastAPI (Python 3.11+) |
| Database | PostgreSQL |
| ORM | SQLAlchemy 2.0 |
| Migrations | Alembic |
| Validation | Pydantic v2 |
| Auth | JWT (python-jose) + bcrypt (passlib) |
| Config | pydantic-settings (.env) |
| Testing | pytest, Swagger UI / Postman |

##  System Architecture

Vyaapaar AI follows a modular architecture that connects voice input, AI processing, business logic, and transaction storage.

```text
             USER
               |
               v
       Voice / Text Input
               |
               v
       Frontend (Next.js)
               |
               v
       Speech Recognition
         (ASR Service)
               |
               v
       AI Processing Layer
       (Intent Extraction)
               |
               v
       Structured Transaction
               |
               v
       Backend API Layer
               |
          +----+------+
          |           |
          v           v
      Database    Business Logic
          |           |
          +-----+-----+
                |
                v
       Digital Khata / Invoices
                |
                v
       AI Business Insights
                |
                v
       Financial Readiness
          Assistance
```

---

### Prerequisites

Make sure you have installed:

- Node.js (LTS version)
- npm
- Git
- A supported database
- Required AI and speech service API credentials

### 1. Clone the Repository

```bash
git clone https://github.com/YOUR-USERNAME/Vyaapaar-AI.git
```

### 2. Navigate to the Project

```bash
cd Vyaapaar-AI
```

### 3. Install Dependencies

For the frontend:

```bash
cd frontend
npm install
```

For the backend, follow its package-specific installation instructions.

### 4. Configure Environment Variables

Create a `.env` file using `.env.example` as a reference.

Example:

```env
DATABASE_URL=
GEMINI_API_KEY=
SARVAM_API_KEY=
```

Add only the credentials required by your actual implementation.

**Important:** Never commit API keys, passwords, or sensitive environment variables to GitHub.

### 5. Run the Application

Start the frontend:

```bash
cd frontend
npm run dev
```

Open:

```text
http://localhost:3000
```

---

## 🔄 Example User Workflow

**Scenario:** A street vendor wants to record a credit transaction.

1. The merchant opens Vyaapaar AI.
2. The merchant records a voice command.
3. The speech recognition system converts speech into text.
4. The AI extracts the transaction details.
5. The backend validates the extracted information.
6. The transaction is stored in the database.
7. The customer's digital Khata is updated.
8. The merchant can view the updated balance and transaction history.

---

##  Target Users

- Street vendors
- Small shop owners
- Kirana store owners
- Local merchants
- Micro-entrepreneurs
- Independent service providers
- Small-scale business operators

---

##  Social Impact

Vyaapaar AI aims to contribute towards:

- **Digital Inclusion:** Making technology accessible to underserved business communities.
- **Financial Awareness:** Helping merchants understand their business transactions.
- **Paperless Record Keeping:** Reducing dependence on traditional notebooks.
- **Financial Readiness:** Helping small businesses maintain organized financial records.
- **Language Accessibility:** Enabling business management through familiar regional languages.

---

##  Future Enhancements

- WhatsApp-based transaction recording.
- Advanced sales analytics and business dashboards.
- Automatic payment reminders for customers.
- Integration with UPI payment systems.
- More regional language support.
- Improved offline-first functionality.
- Business growth recommendations.
- Integration with additional government financial assistance resources.

---

##  Team

**Project:** Vyaapaar AI

**Domain:** Artificial Intelligence | Full-Stack Development | Financial Inclusion

**Built for:** Empowering India's small businesses and micro-entrepreneurs.

| Contributor | Role |
|---|---|
| Aditi Pandey | Backend Engineering |
| Arshpreet kaur | Frontend Engineering |
| Gauri | ML Engineering |

---
---

## Features

- **Authentication** — register, login, JWT tokens, bcrypt password hashing
- **Business-level data isolation** — every record is scoped to a business; ownership verified on every request
- **Customer management** — full CRUD with safe delete (deactivates customers with ledger history)
- **Products** — CRUD with automatic stock adjustment (sales decrement, purchases increment)
- **Transactions** — sale, credit sale (udhar), purchase, expense; server-computed totals (frontend amounts never trusted)
- **Payments** — full and partial payments against customer udhar, linked to specific credit sales
- **Digital Khata** — customer-wise ledger: total credit sales, total payments received, outstanding balance — all computed from actual ledger records
- **Voice integration** — two-step draft/confirm pipeline that receives structured JSON from the AI/speech module and only writes to the ledger after explicit user confirmation
- **Dashboard & reports** — daily / weekly / monthly totals, pending udhar, recent activity
- **Invoices** — server-computed subtotal/tax/total, auto-generated invoice numbers, linked to customers and transactions
- **AI-assistant data endpoints** — read-only, structured financial data for the AI/RAG module (never writes, never touches balances directly)

---

## Money & Safety Guarantees

- All monetary values use `NUMERIC(12,2)` in PostgreSQL and Python `Decimal` — **never floats**
- All totals are computed **server-side** from line items
- **Idempotency keys** on financial writes — duplicate submissions return the original record instead of creating duplicates
- Database is the **single source of truth**; balances are always derived from ledger records
- Secrets live in `.env`, never in code

---

## Project Structure

```javascript
backend/
├── app/
│   ├── main.py               # FastAPI app + error handlers + router wiring
│   ├── config.py             # Settings from .env (pydantic-settings)
│   ├── database.py           # SQLAlchemy engine + session factory
│   ├── models/               # 8 ORM models (User, Business, Customer, Product,
│   │                         #   Transaction, TransactionItem, Payment, Invoice)
│   ├── schemas/              # Pydantic request/response schemas
│   ├── routers/              # 11 route modules (one per feature)
│   ├── services/             # Business logic (totals, ledger math, voice drafts)
│   ├── dependencies/         # JWT auth + business ownership checks
│   └── utils/                # security, money (Decimal), responses, draft store
├── alembic/                  # Database migrations
├── scripts/create_tables.py  # Quick local table creation (no migrations)
├── tests/                    # pytest unit tests
├── requirements.txt
└── .env.example
```

---

## Quickstart (Windows PowerShell)

### 1. Prerequisites

- Python 3.11+ (tick **"Add Python to PATH"** during install)
- PostgreSQL 14+ (remember the postgres password, default port 5432)

### 2. Create the database

In pgAdmin or `psql`:

```sql
CREATE DATABASE vyapaar_sathi;
```

### 3. Setup

```powershell
# Clone / open the project folder, then:
python -m venv venv
venv\Scripts\Activate.ps1

pip install --upgrade pip
pip install -r backend\requirements.txt

# Create your .env
copy backend\.env.example backend\.env

# Generate a secret key and paste it into .env as SECRET_KEY
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

### 4. Configure `.env`

Edit `backend/.env`:

```env
DB_PASSWORD=your_postgres_password     # from PostgreSQL install
SECRET_KEY=paste_generated_key_here    # from step 3
```

### 5. Create tables & run

```powershell
cd backend
python -m scripts.create_tables
uvicorn app.main:app --reload
```

Server starts at **http://127.0.0.1:8000** — interactive docs at **http://127.0.0.1:8000/docs**.

### 6. Run tests

```powershell
cd backend
pytest tests/ -v
```
##  License

This project is intended for educational, innovation, and social-impact purposes.

A suitable open-source license can be added to the repository.

---

**Vyaapaar AI – Turning Every Voice into a Business Record.** 🇮🇳
