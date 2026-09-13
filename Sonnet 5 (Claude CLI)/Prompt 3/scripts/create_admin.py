"""One-off CLI to create an admin account. Admins can't self-register through
the public /register form on purpose. Usage:

    python -m scripts.create_admin admin@example.com "Admin Name"

Prompts for a password (not passed as an argv to avoid shell history leaks).
"""

import getpass
import sys

from sqlalchemy import select

from app.database import SessionLocal
from app.models import Role, User
from app.security import hash_password


def main() -> None:
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)
    email, full_name = sys.argv[1].strip().lower(), sys.argv[2].strip()
    password = getpass.getpass("Password (min 8 chars): ")
    if len(password) < 8:
        print("Password must be at least 8 characters.")
        sys.exit(1)

    db = SessionLocal()
    try:
        if db.scalar(select(User).where(User.email == email)):
            print(f"A user with email {email} already exists.")
            sys.exit(1)
        db.add(User(email=email, password_hash=hash_password(password), full_name=full_name, role=Role.admin))
        db.commit()
        print(f"Created admin {email}.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
