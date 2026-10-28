from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from backend.infrastructure.persistence.models import DepartmentModel, BoardModel, ColumnModel

DEFAULT_COLUMNS = [
    {"ru": "Нужно сделать", "zh": "待办事项", "ky": "Керектуу иштер"},
    {"ru": "Баги", "zh": "缺陷与错误", "ky": "Мүчүлүштүктөр"},
    {"ru": "В процессе фронт", "zh": "前端开发中", "ky": "Фронтенд иштеп жатат"},
    {"ru": "В процессе бэк", "zh": "后端开发中", "ky": "Бэкенд иштеп жатат"},
    {"ru": "На проверке", "zh": "待审核", "ky": "Текшерүүдө"},
    {"ru": "Готово", "zh": "已完成", "ky": "Даяр болду"},
]


@receiver(post_save, sender=DepartmentModel)
def auto_create_board_for_department(sender, instance, created, **kwargs):
    """
    Ensure that whenever a department is created or exists without an active board,
    a default Kanban board with standard 6 columns is automatically generated.
    """
    if not instance.boards.filter(is_archived=False).exists():
        board = BoardModel.objects.create(
            title=instance.name,
            department=instance,
            background_theme="gradient-blue",
            is_archived=False,
        )
        for idx, col in enumerate(DEFAULT_COLUMNS):
            ColumnModel.objects.create(
                board=board,
                title_ru=col["ru"],
                title_zh=col["zh"],
                title_ky=col["ky"],
                original_lang="ru",
                order=idx,
            )


@receiver(post_delete, sender=DepartmentModel)
def cleanup_boards_on_department_delete(sender, instance, **kwargs):
    """
    Remove any associated boards when a department is deleted.
    """
    BoardModel.objects.filter(department=instance).delete()
