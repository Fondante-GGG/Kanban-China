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
from backend.infrastructure.persistence.models import UserModel, OfficeModel, WorkScheduleModel


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

    # Seed default office if none exists
    if OfficeModel.objects.count() == 0:
        OfficeModel.objects.create(
            name="Главный офис Бишкек",
            address="г. Бишкек, пр. Чуй 120",
            latitude=42.8746,
            longitude=74.5698,
            radius_meters=100,
            ip_subnet="",
            is_ip_check_enabled=False
        )
        print("Default office created: Главный офис Бишкек (42.8746, 74.5698, R=100m)")

    # Seed default work schedule if none exists
    if WorkScheduleModel.objects.count() == 0:
        WorkScheduleModel.objects.create(
            name="Стандартный график 9:00 - 18:00",
            start_time="09:00:00",
            end_time="18:00:00",
            break_duration_minutes=60,
            timezone="Asia/Bishkek",
            is_active=True
        )
        print("Default schedule created: 09:00 - 18:00 (Asia/Bishkek)")



if __name__ == "__main__":
    seed()
