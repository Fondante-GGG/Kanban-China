import os
import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone

project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.config.settings")

import django
django.setup()

from django.contrib.auth.hashers import make_password
from backend.infrastructure.persistence.models import (
    UserModel, DepartmentModel, BoardModel, BoardMemberModel, ColumnModel,
    CardModel, CardAssigneeModel, ChecklistModel, CommentModel, ActivityLogModel, NotificationModel
)

def seed():
    print("Seeding initial database data...")

    # Clear old data if any
    NotificationModel.objects.all().delete()
    ActivityLogModel.objects.all().delete()
    CommentModel.objects.all().delete()
    ChecklistModel.objects.all().delete()
    CardAssigneeModel.objects.all().delete()
    CardModel.objects.all().delete()
    ColumnModel.objects.all().delete()
    BoardMemberModel.objects.all().delete()
    BoardModel.objects.all().delete()
    UserModel.objects.all().delete()
    DepartmentModel.objects.all().delete()

    now = datetime.now(timezone.utc)

    # 1. Departments
    dept_it = DepartmentModel.objects.create(name="IT & Разработка")
    dept_marketing = DepartmentModel.objects.create(name="Маркетинг & PR")
    dept_finance = DepartmentModel.objects.create(name="Финансы и Бухгалтерия")

    # 2. Users
    # General Director (Director sees everything)
    director = UserModel.objects.create(
        email="director@company.com",
        password=make_password("password123"),
        full_name="Асанов Асан Асанович (Гендиректор)",
        role="general_director",
        department=dept_it,
        phone="+996 555 102030",
        interface_language="ru",
        is_staff=True,
        is_superuser=True
    )

    # IT Manager
    mgr_it = UserModel.objects.create(
        email="manager.it@company.com",
        password=make_password("password123"),
        full_name="Иванов Иван Иванович (Тимлид IT)",
        role="manager",
        department=dept_it,
        phone="+996 700 112233",
        interface_language="ru",
    )

    # IT Employee
    dev_it = UserModel.objects.create(
        email="dev.it@company.com",
        password=make_password("password123"),
        full_name="Бектур Садыков (Senior Dev)",
        role="employee",
        department=dept_it,
        phone="+996 777 445566",
        interface_language="ky",
    )

    # Marketing Manager
    mgr_mkt = UserModel.objects.create(
        email="manager.marketing@company.com",
        password=make_password("password123"),
        full_name="Ли Вэй / Li Wei (Руководитель маркетинга)",
        role="manager",
        department=dept_marketing,
        phone="+996 500 778899",
        interface_language="zh-Hans",
    )

    # Marketing Employee
    emp_mkt = UserModel.objects.create(
        email="smm.marketing@company.com",
        password=make_password("password123"),
        full_name="Айпери Жумабекова (SMM / PR)",
        role="employee",
        department=dept_marketing,
        phone="+996 550 990011",
        interface_language="ru",
    )

    # 3. Boards
    # Board 1: IT Development
    board_it = BoardModel.objects.create(
        title="Разработка платформы Kanban",
        department=dept_it,
        background_theme="gradient-blue"
    )
    # Board 2: Marketing Campaigns
    board_mkt = BoardModel.objects.create(
        title="Запуск рекламной кампании Q4",
        department=dept_marketing,
        background_theme="gradient-purple"
    )
    # Board 3: Finance Budgeting
    board_fin = BoardModel.objects.create(
        title="Годовой финансовый аудит",
        department=dept_finance,
        background_theme="gradient-emerald"
    )

    # 4. Board Memberships (Strict 1 board rule for manager & employee!)
    BoardMemberModel.objects.create(board=board_it, user=mgr_it, role="manager")
    BoardMemberModel.objects.create(board=board_it, user=dev_it, role="employee")

    BoardMemberModel.objects.create(board=board_mkt, user=mgr_mkt, role="manager")
    BoardMemberModel.objects.create(board=board_mkt, user=emp_mkt, role="employee")

    # 5. Columns for IT Board
    col_todo = ColumnModel.objects.create(
        board=board_it,
        title_ru="Нужно сделать",
        title_zh="待办事项",
        title_ky="Керектуу иштер",
        original_lang="ru",
        order=0
    )
    col_bugs = ColumnModel.objects.create(
        board=board_it,
        title_ru="Баги",
        title_zh="缺陷与错误",
        title_ky="Мүчүлүштүктөр",
        original_lang="ru",
        order=1
    )
    col_front = ColumnModel.objects.create(
        board=board_it,
        title_ru="В процессе фронт",
        title_zh="前端开发中",
        title_ky="Фронтенд иштеп жатат",
        original_lang="ru",
        order=2
    )
    col_back = ColumnModel.objects.create(
        board=board_it,
        title_ru="В процессе бэк",
        title_zh="后端开发中",
        title_ky="Бэкенд иштеп жатат",
        original_lang="ru",
        order=3
    )
    col_review = ColumnModel.objects.create(
        board=board_it,
        title_ru="На проверке",
        title_zh="待审核",
        title_ky="Текшерүүдө",
        original_lang="ru",
        order=4
    )
    col_done = ColumnModel.objects.create(
        board=board_it,
        title_ru="Готово",
        title_zh="已完成",
        title_ky="Даяр болду",
        original_lang="ru",
        order=5
    )

    # Columns for Marketing Board
    m_col_ideas = ColumnModel.objects.create(
        board=board_mkt,
        title_ru="Идеи и гипотезы",
        title_zh="创意与假设",
        title_ky="Идеялар жана гипотезалар",
        original_lang="ru",
        order=0
    )
    m_col_prep = ColumnModel.objects.create(
        board=board_mkt,
        title_ru="Подготовка контента",
        title_zh="内容准备",
        title_ky="Мазмун даярдоо",
        original_lang="ru",
        order=1
    )
    m_col_running = ColumnModel.objects.create(
        board=board_mkt,
        title_ru="В рекламе",
        title_zh="投放中",
        title_ky="Жарнамада",
        original_lang="ru",
        order=2
    )
    m_col_done = ColumnModel.objects.create(
        board=board_mkt,
        title_ru="Завершено",
        title_zh="已结束",
        title_ky="Аяктады",
        original_lang="ru",
        order=3
    )

    # 6. Cards on IT Board
    # Card 1 (In Todo)
    c1 = CardModel.objects.create(
        column=col_todo,
        title_ru="Интеграция многоязычного переводчика",
        title_zh="集成多语言机器翻译服务",
        title_ky="Көп тилдүү котормочу кызматын интеграциялоо",
        desc_ru="Необходимо подключить автоматический машинный перевод для русского, китайского и кыргызского языков.",
        desc_zh="需要为俄语、中文和吉尔吉斯语接入免费的自动机器翻译服务。",
        desc_ky="Орус, кытай жана кыргыз тилдери үчүн акысыз автоматтык машиналык котормону туташтыруу зарыл.",
        original_lang="ru",
        priority="high",
        due_date=now + timedelta(days=5),
        order=0,
        created_by=mgr_it
    )
    CardAssigneeModel.objects.create(card=c1, user=dev_it)
    ChecklistModel.objects.create(card=c1, title="Подключить переводчик", is_completed=True, order=0)
    ChecklistModel.objects.create(card=c1, title="Проверить кыргызский язык", is_completed=False, order=1)
    ChecklistModel.objects.create(card=c1, title="Добавить поддержку китайских иероглифов", is_completed=False, order=2)
    CommentModel.objects.create(
        card=c1,
        user=mgr_it,
        text_ru="Проверьте скорость работы перевода на больших текстах.",
        text_zh="请检查长文本翻译的处理速度。",
        text_ky="Чоң тексттерди которуунун ылдамдыгын текшериңиз.",
        original_lang="ru"
    )

    # Card 2 (In Bugs)
    c2 = CardModel.objects.create(
        column=col_bugs,
        title_ru="Исправить горизонтальный скролл на мобильных устройствах",
        title_zh="修复移动端看板水平滚动的布局问题",
        title_ky="Мобилдик телефондордогу туурасынан жылдырууну оңдоо",
        desc_ru="На экранах шириной меньше 768px колонки должны плавно прокручиваться по горизонтали.",
        desc_zh="在宽度小于768px的屏幕上，看板列应平滑水平滑动。",
        desc_ky="Туурасы 768px төмөн экрандарда тилкелер жылмакай жылышы керек.",
        original_lang="ru",
        priority="urgent",
        due_date=now - timedelta(days=1), # overdue
        order=0,
        created_by=director
    )
    CardAssigneeModel.objects.create(card=c2, user=dev_it)

    # Card 3 (In Frontend)
    c3 = CardModel.objects.create(
        column=col_front,
        title_ru="Реализация Drag-and-Drop карточек с плавными анимациями",
        title_zh="实现流畅动画的卡片拖拽 (Drag & Drop) 功能",
        title_ky="Карточкаларды жылдыруучу ыңгайлуу Drag & Drop түзүү",
        desc_ru="Добавить перетаскивание между колонками с сохранением порядка на сервере.",
        desc_zh="添加列之间拖动卡片的功能，并将新的排序状态保存到后端。",
        desc_ky="Тилкелер ортосунда карточкаларды сүйрөп жылдырууну жана серверге сактоону кошуу.",
        original_lang="ru",
        priority="high",
        due_date=now + timedelta(days=3),
        order=0,
        created_by=mgr_it
    )
    CardAssigneeModel.objects.create(card=c3, user=dev_it)
    ChecklistModel.objects.create(card=c3, title="Выбрать drag-and-drop библиотеку", is_completed=True, order=0)
    ChecklistModel.objects.create(card=c3, title="Настроить сохранение позиции", is_completed=True, order=1)

    # Card 4 (In Backend)
    c4 = CardModel.objects.create(
        column=col_back,
        title_ru="Реализация архитектуры Clean Architecture + DDD + UoW",
        title_zh="在后端实现 Clean Architecture + DDD + UoW 架构",
        title_ky="Бэкендде Clean Architecture + DDD + UoW архитектурасын ишке ашыруу",
        desc_ru="Выделить Domain, Application, Infrastructure и Presentation слои, внедрить Dependency Injection.",
        desc_zh="划分领域层、应用层、基础设施层和表现层，引入依赖注入 (DI)。",
        desc_ky="Domain, Application, Infrastructure жана Presentation катмарларын бөлүп, Dependency Injection киргизүү.",
        original_lang="ru",
        priority="urgent",
        due_date=now + timedelta(days=2),
        order=0,
        created_by=director
    )
    CardAssigneeModel.objects.create(card=c4, user=mgr_it)

    # Card 5 (In Done)
    c5 = CardModel.objects.create(
        column=col_done,
        title_ru="Разработка системы разграничения прав RBAC",
        title_zh="开发基于角色的访问控制系统 (RBAC)",
        title_ky="Ролдор боюнча кирүү укуктарын башкаруу системасын иштеп чыгуу",
        desc_ru="Генеральный директор видит все доски, руководитель и сотрудник только свою.",
        desc_zh="总经理可以查看所有部门的看板，主管和员工仅能访问自己被分配的看板。",
        desc_ky="Башкы директор бардык такталарды көрөт, жетекчи жана кызматкер өзүнүкүн гана көрөт.",
        original_lang="ru",
        priority="medium",
        due_date=now - timedelta(days=3),
        order=0,
        created_by=mgr_it
    )
    CardAssigneeModel.objects.create(card=c5, user=dev_it)
    CardAssigneeModel.objects.create(card=c5, user=mgr_it)

    # 7. Notifications
    NotificationModel.objects.create(
        user=dev_it,
        title="Назначена новая задача",
        message="Вы назначены на задачу: «Интеграция многоязычного переводчика»",
        entity_type="card",
        entity_id=c1.id,
        is_read=False
    )
    NotificationModel.objects.create(
        user=dev_it,
        title="Срочная задача!",
        message="Вам назначена задача «Исправить горизонтальный скролл на мобильных устройствах»",
        entity_type="card",
        entity_id=c2.id,
        is_read=False
    )

    print("Database seeding completed successfully!")
    print("Default Test Accounts:")
    print("1. General Director: director@company.com / password123")
    print("2. IT Manager:       manager.it@company.com / password123")
    print("3. IT Employee:      dev.it@company.com / password123")
    print("4. Mkt Manager:      manager.marketing@company.com / password123")
    print("5. Mkt Employee:     smm.marketing@company.com / password123")

if __name__ == "__main__":
    seed()
