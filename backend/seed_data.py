import os
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.config.settings")

import django
django.setup()

from django.contrib.auth.hashers import make_password
from backend.infrastructure.persistence.models import UserModel


def seed():
    """
    Initial bootstrap script.
    Creates a default administrator only if the database is completely empty.
    Never inserts test accounts or dummy cards.
    """
    if UserModel.objects.count() == 0:
        UserModel.objects.create(
            email="admin@gmail.com",
            password=make_password("admin12345"),
            full_name="Администратор",
            role="general_director",
            interface_language="ru",
            is_staff=True,
            is_superuser=True
        )
        print("Initial admin user created: admin@gmail.com / admin12345")
    else:
        print("Database already contains users. Skipping initial seed.")


if __name__ == "__main__":
    seed()
