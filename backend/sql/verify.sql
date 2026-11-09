-- Run in pgAdmin Query Tool connected to postmate_db.
SELECT current_database(), version();
SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename;
SELECT * FROM alembic_version;
SELECT id, username, full_name, role, active, created_at FROM users ORDER BY created_at;
SELECT id, user_id, phone, post_office, agent_id FROM staff_profiles;
-- Aadhaar and PAN ciphertext intentionally excluded; use the audited API for identity access.
SELECT customer_code, full_name, phone, post_office, staff_id, active, deleted_at FROM customers ORDER BY created_at DESC;
SELECT code, name, active, frequency_months, duration_months, schedule_kind FROM schemes ORDER BY code;
SELECT s.code, f.key, f.label, f.field_type, f.required FROM scheme_fields f JOIN schemes s ON s.id=f.scheme_id ORDER BY s.code, f.key;
SELECT a.account_code, c.customer_code, c.full_name, s.code, a.account_number, a.policy_number,
       a.amount, a.start_date, a.nominee_name, a.maturity_date, a.maturity_amount, a.status, a.deleted_at
FROM customer_scheme_accounts a JOIN customers c ON c.id=a.customer_id JOIN schemes s ON s.id=a.scheme_id;
SELECT a.account_code, p.sequence, p.due_date, p.expected_amount, p.paid_amount,
       CASE WHEN p.cancelled THEN 'Cancelled' WHEN p.paid_amount >= p.expected_amount THEN 'Paid'
            WHEN p.due_date < (now() AT TIME ZONE 'Asia/Kolkata')::date THEN 'Overdue'
            WHEN p.paid_amount > 0 THEN 'Partially Paid'
            WHEN p.due_date = (now() AT TIME ZONE 'Asia/Kolkata')::date THEN 'Due' ELSE 'Upcoming' END AS status
FROM payment_schedules p JOIN customer_scheme_accounts a ON a.id=p.account_id ORDER BY p.due_date;
SELECT t.id, t.amount, t.payment_date, t.method, t.staff_id, t.reference, t.reversed_at,
       t.reversal_reason, t.deleted_at, r.receipt_number, r.download_count
FROM payment_transactions t JOIN payment_receipts r ON r.transaction_id=t.id ORDER BY t.created_at DESC;
SELECT id, customer_id, kind, content_type, size, uploaded_by FROM customer_documents;
SELECT n.id, n.kind, n.resolved, p.due_date, p.account_id FROM notifications n JOIN payment_schedules p ON p.id=n.schedule_id;
SELECT created_at, user_id, action, entity_type, entity_id, details FROM audit_logs ORDER BY created_at DESC LIMIT 100;
-- These reconciliation queries should return ZERO rows.
SELECT p.id, p.paid_amount, COALESCE(SUM(t.amount) FILTER (WHERE t.reversed_at IS NULL),0) AS ledger_sum
FROM payment_schedules p LEFT JOIN payment_transactions t ON t.schedule_id=p.id
GROUP BY p.id HAVING p.paid_amount <> COALESCE(SUM(t.amount) FILTER (WHERE t.reversed_at IS NULL),0);
SELECT t.id FROM payment_transactions t LEFT JOIN payment_receipts r ON r.transaction_id=t.id WHERE r.id IS NULL;
