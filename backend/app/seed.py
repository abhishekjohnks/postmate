"""Development-only, idempotent seeding. Password is prompted, never supplied in CLI args."""
from getpass import getpass
import argparse
from pathlib import Path
import secrets
from sqlalchemy import select
from app.core.security import passwords
from app.db.session import SessionLocal
from app.models import Scheme, SchemeField, User

DEFINITIONS = [
    ("RD", "Recurring Deposit", 1, 60, "collection", False, ["account_number", "cif_id"]),
    ("PLI", "Postal Life Insurance", 1, None, "collection", False, ["policy_number"]),
    ("RPLI", "Rural Postal Life Insurance", 1, None, "collection", False, ["policy_number"]),
    ("TD1", "Time Deposit · 1 Year", 0, 12, "collection", False, ["account_number"]),
    ("TD2", "Time Deposit · 2 Years", 0, 24, "collection", False, ["account_number"]),
    ("TD5", "Time Deposit · 5 Years", 0, 60, "collection", False, ["account_number"]),
    ("SSA", "Sukanya Samriddhi Account", None, 252, "discretionary", False, ["account_number"]),
    ("PPF", "Public Provident Fund", None, 180, "discretionary", False, ["account_number"]),
    ("SCSS", "Senior Citizens' Savings Scheme", 0, None, "income", False, ["account_number"]),
    ("MIS", "Monthly Income Scheme", 0, None, "income", False, ["account_number"]),
    ("MAHILA", "Mahila Samman Savings Certificate", 0, None, "collection", True, ["account_number"]),
]


def seed_schemes(db):
    for code, name, frequency, duration, kind, historical, required in DEFINITIONS:
        existing = db.scalar(select(Scheme).where(Scheme.code == code))
        if existing:
            # Upgrade only the previously unspecified terms of these templates.
            # Account dates and explicitly configured scheme terms are retained.
            if code in {"SSA", "PPF"} and existing.duration_months is None:
                existing.duration_months = duration
            continue
        scheme = Scheme(code=code, name=name, frequency_months=frequency, duration_months=duration,
                        schedule_kind=kind, historical_only=historical,
                        description="Development template. Verify identifiers, duration, due dates and rules against the actual Post Office record before use. "
                                    + ("Interest payouts are not payment collections; only the opening deposit is scheduled." if kind == "income" else ""))
        db.add(scheme)
        db.flush()
        for key in ["account_number", "policy_number", "cif_id"]:
            if key == "policy_number" and code not in {"PLI", "RPLI"}:
                continue
            if key != "policy_number" and code in {"PLI", "RPLI"}:
                continue
            db.add(SchemeField(scheme_id=scheme.id, key=key, label={"account_number": "Account number", "policy_number": "Policy number", "cif_id": "CIF ID"}[key], required=key in required))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--generate-admin', action='store_true', help='Generate local admin credentials in ignored .initial-admin.txt instead of prompting')
    args = parser.parse_args()
    generated = None
    with SessionLocal.begin() as db:
        if not db.scalar(select(User).where(User.role == "super_admin")):
            username = 'admin' if args.generate_admin else input("Super Admin username: ").strip().lower()
            if len(username) < 3:
                raise SystemExit("Username must contain at least 3 characters")
            password = secrets.token_urlsafe(24) if args.generate_admin else getpass("Super Admin password (12+ characters): ")
            if len(password) < 12 or (not args.generate_admin and password != getpass("Confirm password: ")):
                raise SystemExit("Password too short or confirmation does not match")
            db.add(User(username=username, full_name="Super Admin", role="super_admin", password_hash=passwords.hash(password)))
            if args.generate_admin:
                generated = f'PostMate local development login\nUsername: {username}\nPassword: {password}\n'
        seed_schemes(db)
    if generated:
        path = Path(__file__).resolve().parents[1] / '.initial-admin.txt'
        path.write_text(generated, encoding='utf-8')
        print('Generated local credentials saved to ignored backend/.initial-admin.txt')
    print("Development seed complete; existing accounts and schemes retained.")


if __name__ == "__main__":
    main()
