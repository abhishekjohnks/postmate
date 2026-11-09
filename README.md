# PostMate

React + FastAPI + PostgreSQL workspace for postal savings and insurance records. All application records come from PostgreSQL; the interface has empty states until real records are entered. pgAdmin is a database administration client and does not need a special application integration.

## Included

- Super Admin and Staff dashboards, JWT login, Argon2 password hashing, expiring sessions and server-side logout revocation.
- Staff creation, updates and activation/deactivation. Staff can access only customers assigned to them, including account schedules, transactions, private documents, receipts, dashboards and exports. Admin can reassign customers.
- Customer records with encrypted Aadhaar/PAN, masked lists and authorized eye buttons to reveal/hide individual identity numbers. Access is logged automatically without a remarks prompt.
- Ten development scheme definitions, dynamic identifiers/custom fields, configurable month intervals, single deposits, discretionary deposits, maturity terms and historical-only accounts.
- Calendar-anchored schedules, live payment status, partial payments when explicitly enabled, excess-payment rejection, duplicate request protection, original ledger retention and admin-only reversals.
- Transactional payment + balance + receipt creation, immutable receipt snapshots, PDF download/reprints and download audit records.
- Modern PDF receipts highlight the payment amount, customer and account details. Customer IDs, staff IDs and internal `PM-...` references are retained in PostgreSQL but omitted from the printed receipt and download filename.
- Encrypted PDF/PNG/JPEG uploads up to 5 MB, format verification and authorized downloads. Private files have no static/public URL.
- Role-scoped metrics, collection charts, maturity alerts, due notifications, searchable tables, pagination, CSV reports and admin audit trail.
- Alembic migration, idempotent development seed, SQL verification queries and PostgreSQL integration tests.

## Requirements

- Python 3.11+; Node.js **22 LTS** (or 20.19+), npm; PostgreSQL 16+; pgAdmin 4.
- This checkout was built with the host's Node 21.2, which is outside Vite's supported release range. Use Node 22 for ongoing development.

## 1. PostgreSQL and pgAdmin

Install PostgreSQL and pgAdmin 4. During installation set a local `postgres` password. Start the PostgreSQL service.

In pgAdmin: **Register → Server**. Choose a name, then under Connection set host `localhost`, port `5432`, maintenance database `postgres`, username `postgres`, and your password. Under Databases choose **Create → Database**, name it `postmate_db`, and use an appropriate owner (the initial local example uses `postgres`).

Alternatively, after configuring the backend environment, run `python scripts/create_database.py` from `backend`. This explicit helper creates the database only if absent; application startup never creates databases or tables.

## 2. Backend setup (PowerShell)

```powershell
cd D:\PostMate\backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.lock.txt
Copy-Item .env.example .env
```

The lock file pins the tested Python environment. `requirements.txt` lists the supported direct dependency ranges for intentional upgrades.

Edit `backend/.env`. Set `POSTGRES_PASSWORD` to your local PostgreSQL password. Never commit `.env`. Generate independent application keys:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Put the first value in `JWT_SECRET` and the second in `ENCRYPTION_KEY`. Keep the encryption key safe: existing identity values and uploaded documents cannot be decrypted without it. The SQLAlchemy connection uses `URL.create`, so special characters in database passwords are escaped correctly. Paths and `.env` are resolved relative to the backend working directory.

Alternatively, `python scripts/configure_local.py` prompts for the database password and creates `.env` with generated keys when the file is absent. It never overwrites existing settings. Use manually managed secrets outside development.

## 3. Migrate and create the Super Admin

```powershell
# Still in backend, with the virtual environment active
alembic upgrade head
python -m app.seed
```

The development seed prompts for the initial admin username and a password of at least 12 characters. It inserts missing scheme definitions only and never resets existing credentials or overwrites configuration. There is no fixed/default admin password.

For an unattended **local development** bootstrap:

```powershell
python -m app.seed --generate-admin
```

This creates username `admin` with a random password, saved in the gitignored `backend/.initial-admin.txt`. If an admin already exists, it is retained. Delete the credential file after storing the password securely.

Migrations and seed are explicit commands; restarting FastAPI cannot duplicate data. Future schema changes:

```powershell
alembic revision --autogenerate -m "describe change"
# Review the generated migration before applying it
alembic upgrade head
alembic check
```

## 4. Start backend and frontend

After completing setup, migrations and seeding, double-click **[Start-PostMate.bat](Start-PostMate.bat)** in `D:\PostMate`. It starts the backend and frontend in separate terminal windows and opens the application in your browser. Keep these windows open while using PostMate; press **Ctrl+C** in each server window to stop it. PostgreSQL must already be running. The launcher uses its own directory, so it also works through a desktop shortcut, and reuses ports 8000/5173 when servers are already running. Other applications should not use these ports.

Run `Start-PostMate.bat --check` to verify startup prerequisites without starting servers or opening the browser. The launcher starts existing installations; it does not install packages, change credentials or run migrations.

Alternatively, start the servers manually:

Terminal 1:

```powershell
cd D:\PostMate\backend
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Terminal 2:

```powershell
cd D:\PostMate\frontend
npm ci
npm run dev
```

Open **http://localhost:5173**. Sign in with the seeded admin credentials. The Vite development proxy forwards `/api` to FastAPI. For a separately hosted frontend set `VITE_API_URL` at build time and configure an exact backend `CORS_ORIGINS` list. `npm run build` creates `frontend/dist`; a production static host needs an SPA fallback to `index.html` and an API reverse proxy or configured API origin.

Tokens remain in browser memory and expire after 30 minutes by default. Reloading the page requires signing in again. Sign out revokes all tokens for the current user. Staff deactivation or a staff password reset also revokes existing tokens. The login endpoint limits attempts per client IP within one process.

## 5. First workflow

For flexible deposit setup, day/month/year date entry, and the exact files to copy when updating another laptop, see [UPDATE-OTHER-LAPTOP.md](UPDATE-OTHER-LAPTOP.md).

Flexible account cards now provide **Record deposit** for entering the paid amount and date directly, generating a receipt in the same transaction. They show total deposits and SSA/PPF financial-year summaries; the annual INR 1,50,000 limit is enforced on recorded payments. Completed-year minimum shortfalls are flagged for review, not automatic closure. Date inputs support both dd/mm/yyyy typing and a calendar picker.

1. In **Staff members**, create a staff user with a unique username and 12+ character password. Staff creation has a fixed Staff role. Only the seeded Super Admin exists; API validation and a PostgreSQL partial unique index prevent creating or promoting a second Super Admin. The Super Admin record is protected from staff-management changes.
2. Review **Scheme settings** and verify the configured identifiers, frequency, maturity term and partial-payment policy against the actual Post Office record.
3. Open **Customers & schemes → Add customer**. Enter personal details and choose the staff assignment. Staff-created customers are automatically assigned to that staff member.
4. In the same form select a savings or insurance scheme, enter its identifiers, amount and dates, and use **Add another scheme** for additional accounts. **Create customer & schemes** saves the customer, accounts and schedules together in one transaction. Insurance with no default term requires an explicit maturity date for bounded recurring collection schedules. Open an existing customer and choose **Add scheme**, or edit their customer record, to link more schemes later. The **All scheme accounts** tab provides account search, schedules, history, status changes and discretionary deposit actions.

   Each scheme account also has an optional **Nominee name**. Customer profiles and the account list show the nominee and account opening date. Use the account pencil action to add or update a nominee on an existing account.

   Enter **Maturity amount (INR, optional)** for each scheme using the expected amount from the account/policy record. Customer profiles and the account list show this amount, the full opening-to-maturity term, and the time remaining from today in calendar years, months and days. Durations are calculated using the configured application timezone; matured accounts show zero remaining time. Missing amounts/dates show **Not recorded** rather than an estimated value. Existing accounts can add or update the maturity amount using the pencil action. The maturity amount is entered manually, independently of deposits and payment balances.
5. For discretionary schemes, use the account's calendar action to add individual agreed deposits. RD generates monthly collections; TD generates a single opening deposit. Income schemes collect the opening deposit once.
6. From **Payment dues**, select an instalment and record its actual amount, date and method. Download the PDF or re-download it from Transactions.
7. Use **Reports** for filtered collection and due exports. Each batch contains up to 1,000 rows by default; increment the export batch for larger datasets. API clients can request up to 10,000 rows per batch.
8. Use the trash button to delete a transaction after confirming. Its amount becomes outstanding again, and the instalment appears in payment dues according to its due date. Deletion reverses the payment and hides it from the active list; the original record and receipt remain traceable. **Show deleted transactions** displays this history. Repeated deletion cannot restore the amount twice. Admin can also reverse a payment explicitly with a reason.
9. Only Super Admin can delete customers, scheme accounts, transactions or uploaded documents. The API independently rejects Staff deletion requests, including requests for their own assigned records. Customer and account trash buttons remove records from operational lists and suppress their future dues. These are soft deletions: historical payments, receipts and database relationships are retained. Deleting a customer or account does not refund or reverse existing collections; delete the relevant transaction separately when correcting a payment.
10. Sign out is in the top bar for both roles. Customer details omit the internal Customer ID. Under **Private documents**, choose **Preview** to view Aadhaar/PAN images or PDFs inside the application, with zoom controls and PDF page navigation. Preview requests require authentication and customer ownership permissions; private storage paths are never exposed. PDF pages are rasterized on the backend rather than executing uploaded PDF content in the browser.

Inactive customers/accounts cannot receive payments. Payment amounts cannot exceed the instalment balance. Partial payments are allowed only if enabled in the account's saved rule snapshot. Payment dates must be between the account start and today. Backdated records may immediately appear overdue.

## 6. Swagger and verification through pgAdmin

- Swagger UI: **http://127.0.0.1:8000/docs**; OpenAPI: `/openapi.json`; database health: `/health`.
- In Swagger, **Authorize** uses the same username/password login. Roles and ownership are enforced by FastAPI, independently of React.
- Payments require an `Idempotency-Key` header of 16–100 characters. Retry the same payload with the same key after an uncertain response. A changed payload with a reused key is rejected. The UI preserves the key across retries.
- In pgAdmin refresh **postmate_db → Schemas → public → Tables**. Right-click a table → **View/Edit Data**, or open Query Tool and run [backend/sql/verify.sql](backend/sql/verify.sql).
- For a read-only command-line schema/ledger check, run `python scripts/verify_database.py` from `backend`. It prints record counts and checks balance reconciliation and missing receipts without printing identities or credentials.
- There are twelve domain tables plus `alembic_version`. Staff/customer ownership is normalized through `customers.staff_id`, accounts through `customer_id`, and schedule customer/staff context through joins. Personal documents store only metadata in PostgreSQL; encrypted bytes are stored under `backend/storage`.
- Identity values in PostgreSQL are ciphertext by design. Use the authorized, audited customer identity action when full values are necessary. Do not edit ledger rows directly in pgAdmin; this bypasses validation, balance updates, receipts and audit events.

## 7. Tests

Run against the migrated local PostgreSQL database:

```powershell
cd D:\PostMate\backend
.\.venv\Scripts\python -m pytest -q
```

Tests use real PostgreSQL transactions and nested savepoints, rolling all fixture records back after each test. No SQLite/mocked database is substituted. They cover ownership isolation, encrypted identities and documents, unauthorized downloads, dynamic schedule types, month-end calendar anchoring, partial/excess payments, idempotency, receipt reprints, reversals, token revocation, reports and dashboards. Document fixtures use temporary storage. Do not run development tests against production.

```powershell
cd D:\PostMate\frontend
npm run build
```

Optional desktop/mobile browser checks use the running local servers and the generated local admin credential file:

```powershell
cd D:\PostMate\frontend
npm run test:e2e
```

Playwright uses locally installed Chrome on Windows by default. Set `PLAYWRIGHT_CHROME_PATH` to your Chrome executable on another system. These browser checks exercise login/logout, navigation, dynamic account fields, form validation, mobile overflow and keyboard dialog dismissal without inserting customer or payment records. Screenshots are saved under the ignored `frontend/test-results` directory.

## Architecture and operational boundaries

`backend/app/api` contains REST modules; `core` contains configuration/security; `db` owns sessions; `models.py` owns SQLAlchemy mappings; `schemas.py` defines request validation; `repositories.py` centralizes ownership access; `services` implements account schedules, ledger operations, PDFs and notification refresh. Every request commits its business changes and audit records together or rolls back. Payment writes lock the instalment row in PostgreSQL and use database uniqueness constraints. Receipts preserve customer/account details at the time of collection. JSON scheme fields extend the relational core without adding scheme-specific tables.

The scheduled task upserts one notification per due event every 15 minutes, updates its kind, and resolves paid/cancelled/inactive events. Dashboard and notification APIs read current ledger conditions between refreshes. Run **one application process** with `ENABLE_SCHEDULER=true`; for multiple API workers disable their schedulers and run a single external scheduled invocation of `python -c "from app.services.notifications import refresh_notifications; refresh_notifications()"`. Email/SMS/WhatsApp delivery is not configured.

Scheme seeds are development templates, **not an authoritative implementation of India Post regulations**. There is no interest calculator, disbursement ledger, late-fee engine or automated scheme eligibility decision. Income scheme interest payout details can be stored as configurable account fields; automatic payout schedules are a future extension separate from customer collections. Early closure, term extensions, irregular holidays, policy-specific premium cessation, SSA deposit windows and specialized maturity rules require reviewed configuration or further business logic before operational use. Existing financial schedule terms cannot be silently rewritten through ordinary account edits; account edits cover status and remarks, while discretionary deposits and admin schedule cancellations have explicit endpoints.

Document files are encrypted with the same configured Fernet key as identity values. Back up PostgreSQL, encrypted storage and the key together. File contents are checked, but malware scanning and content disarm are not provided; integrate a scanner before allowing untrusted document intake in production. Documents download as attachments. Application files and audit trails are not a substitute for database backup or immutable external audit retention.

For production use a dedicated database role, HTTPS, a reverse proxy with shared login rate limiting and request-size limits, managed secret storage, key rotation procedures, monitored background jobs, restricted host storage permissions, tested backups, and reviewed access/retention rules. Run migrations as a deployment step, not startup. Configure a Unicode TrueType font in receipt rendering if customer names require non-Latin scripts (the bundled PDF base fonts cover Latin text).

Authentication and database transaction patterns follow [FastAPI's JWT/Argon2 guidance](https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/) and [SQLAlchemy transaction documentation](https://docs.sqlalchemy.org/en/20/orm/session_transaction.html).
#   p o s t m a t e  
 