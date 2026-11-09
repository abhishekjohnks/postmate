"""Create ignored local settings without printing secrets. Never overwrites .env."""
from pathlib import Path
from getpass import getpass
import secrets
from cryptography.fernet import Fernet

target = Path(__file__).resolve().parents[1] / ".env"
if target.exists():
    print("Existing .env retained")
else:
    template = target.with_name(".env.example").read_text()
    database_password = getpass('Local PostgreSQL password: ')
    if not database_password:
        raise SystemExit('A database password is required')
    # python-dotenv safely parses a single-quoted value with escaped quotes/backslashes.
    escaped_password = database_password.replace('\\', '\\\\').replace("'", "\\'")
    template = template.replace("replace-with-your-local-password", "'" + escaped_password + "'")
    template = template.replace("replace-with-at-least-32-random-characters", secrets.token_urlsafe(48))
    template = template.replace("replace-with-generated-fernet-key", Fernet.generate_key().decode())
    target.write_text(template, encoding="utf-8")
    print("Created ignored backend/.env with generated keys and your local database password")
