"""Create the first admin user. Usage: python seed_admin.py email password "Name" """
import sys

from dotenv import load_dotenv

load_dotenv()

from app import create_app
from app.extensions import db
from app.models import User, ROLE_ADMIN


def main():
    if len(sys.argv) != 4:
        print('Usage: python seed_admin.py <email> <password> "<name>"')
        sys.exit(1)

    email, password, name = sys.argv[1], sys.argv[2], sys.argv[3]
    app = create_app()
    with app.app_context():
        if User.query.filter_by(email=email).first():
            print(f"User {email} already exists.")
            sys.exit(1)
        admin = User(email=email.lower(), name=name, role=ROLE_ADMIN)
        admin.set_password(password)
        db.session.add(admin)
        db.session.commit()
        print(f"Admin user {email} created.")


if __name__ == "__main__":
    main()
