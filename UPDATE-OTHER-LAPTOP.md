# Flexible deposits and dd/mm/yyyy update

## Changed application files

Copy these files to the same relative paths on the other laptop:

```text
backend/app/schemas.py
backend/app/services/accounts.py
backend/app/api/schemes.py
backend/app/api/accounts.py
backend/app/seed.py
frontend/src/components/DateInput.jsx                 (new)
frontend/src/components/UI.jsx
frontend/src/components/SchemeFields.jsx
frontend/src/components/CustomerAccountCard.jsx
frontend/src/pages/Admin.jsx
frontend/src/pages/Accounts.jsx
frontend/src/pages/Customers.jsx
frontend/src/pages/Dashboard.jsx
frontend/src/pages/Payments.jsx
README.md
UPDATE-OTHER-LAPTOP.md                               (new)
```

Optional test files, if you run the development checks there:

```text
backend/tests/test_flexible_deposits.py
frontend/tests/date-input.spec.js
frontend/tests/fixtures/date-input.html
```

## Apply on the other laptop

1. Stop the frontend and backend windows.
2. Back up the other laptop's database, document storage, and backend `.env`.
3. Copy the files listed above. Keep that laptop's `.env`, storage, and database; this code update does not require replacing them.
4. Add the missing PPF scheme template with the idempotent seed command, from the project folder:

   ```powershell
   cd backend
   .\.venv\Scripts\python.exe -m app.seed
   ```

   Existing users, scheme configuration, customers and payments are retained. An existing Super Admin's password is not changed. No schema migration or additional package installation is needed for this update.
   The seed now fills previously blank SSA/PPF scheme terms with 252 months (21 years) and 180 months (15 years). Explicitly configured terms and existing account dates are retained.
5. Double-click `Start-PostMate.bat`. Refresh the browser.

## Use flexible deposits

In Scheme settings, choose **Flexible deposits — no fixed schedule (SSA / PPF)** for the Collection type. Frequency in months is disabled. This changes the default for new accounts, not the saved rules or schedules of existing accounts.

When creating a customer/account, a flexible scheme automatically displays **Flexible deposits — no fixed schedule**. Other schemes can explicitly select that payment frequency when the actual account records call for irregular deposits. The required **Reference deposit amount** is informational; saving the account does not record a payment or create monthly dues.

In a customer account card or All scheme accounts, use **Record deposit** to enter the amount received and date paid. Saving creates the deposit and payment receipt together. A deposit can be INR 100 now and INR 500 three months later. Months without an agreed deposit have no automatically generated dues. An explicitly scheduled but unpaid deposit still appears as due/overdue. SSA/PPF payments are limited to INR 1,50,000 per account per financial year based on payment date and non-reversed transactions.

Existing account rules are retained. Do not recreate an account that has financial history just to change its payment mode; an audited schedule conversion is a separate change.

Date inputs throughout the application now accept `dd/mm/yyyy`, including date of birth, opening/maturity dates, payment dates, custom scheme date fields, and filters. For example, enter `04/11/2026` for 4 November 2026. The API and PostgreSQL continue to receive ISO dates. Invalid dates and out-of-range form dates are rejected.

## SSA and PPF terms update

SSA defaults to 21 years from opening. PPF defaults to 15 complete financial years after the end of the opening financial year, so its default maturity date is 31 March. Explicit maturity dates can still be entered from the actual account record. Existing account dates are not rewritten by the seed.

Neither flexible account creation nor editing requests a maturity amount. The customer card omits it and the mixed account table displays “Unknown — flexible deposits”. The backend rejects new fixed maturity amounts for flexible accounts.

SSA guidance displays INR 250 minimum / INR 1,50,000 maximum per financial year and a 15-year deposit period within the 21-year term. PPF guidance displays INR 500 minimum / INR 1,50,000 maximum per financial year. The maximum is checked when recording payments; annual minimums appear in the customer account breakdown. Statutory deposit windows, initial deposit minimums, deposit multiples, combined guardian/minor PPF limits, penalties, revival and interest are not automatically enforced.

For this follow-up only, copy `backend/app/seed.py`, `backend/app/services/accounts.py`, `backend/app/api/accounts.py`, `frontend/src/components/SchemeFields.jsx`, `frontend/src/components/CustomerAccountCard.jsx`, `frontend/src/pages/Accounts.jsx`, and this document. The updated `backend/tests/test_flexible_deposits.py` is optional. Run the seed command above and restart both servers.

## Calendar picker and direct deposits update (5 November 2026)

For this update, copy these application files to the same paths:

```text
backend/app/schemas.py
backend/app/api/payments.py
backend/app/api/accounts.py
backend/app/services/ledger.py
backend/app/services/deposits.py                      (new)
frontend/src/components/DateInput.jsx
frontend/src/components/DateInput.css                 (new)
frontend/src/components/CustomerAccountCard.jsx
frontend/src/components/SchemeFields.jsx
frontend/src/pages/Customers.jsx
frontend/src/pages/Accounts.jsx
frontend/src/pages/Payments.jsx
README.md
UPDATE-OTHER-LAPTOP.md
```

Optional tests: `backend/tests/test_direct_deposits.py`, `frontend/tests/date-input.spec.js`, `frontend/tests/direct-deposit.spec.js`, `frontend/tests/fixtures/direct-deposit.html`.

Restart the backend and frontend after copying. No new packages, schema migration or seed command is required for this update. Apply earlier updates first if the other laptop does not have them. Retain its `.env`, database and storage.

Date inputs retain `dd/mm/yyyy` text entry and now include a calendar icon with a native browser picker. The browser calendar's own appearance follows Windows/browser settings; the visible text input remains day/month/year.

**Record deposit** saves the amount, payment date, payment method and optional reference/remarks atomically with a schedule, transaction and receipt. Retry protection prevents a repeated submission from creating another deposit. Previously created unpaid schedules should be paid through Payment dues; recording a new direct deposit does not settle an existing scheduled due.

Customer account cards show total recorded deposits (excluding interest, reversed and deleted payments), plus annual totals for SSA/PPF. Totals are based on payment dates in April–March financial years. Current-year minimums remain pending until year end. Completed-year shortfalls are flagged for review, including years with no recorded deposits. SSA reviews minimums only during the deposit period. Historical records may be incomplete, so verify shortfalls against the actual passbook.

Accounts are not automatically closed for annual shortfalls. Official rules distinguish SSA default and PPF discontinuation, with possible regularisation; these require review of the official account. This application does not implement statutory revival or automatic closure. A payment taking an SSA/PPF account above INR 1,50,000 in a financial year is rejected, through either direct deposits or the existing scheduled-payment endpoint. Reversals release the amount from the recorded annual total.

Sources: [SSA scheme rules](https://www.nsiindia.gov.in/writereaddata/SchemeRules/SukanyaSamriddhiAccountSchemeRule.pdf), [PPF FAQ](https://sbi.bank.in/en/web/faq-s/faq-public-provident-fund).
