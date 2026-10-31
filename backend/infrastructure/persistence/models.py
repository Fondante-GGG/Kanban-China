from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils import timezone
from backend.infrastructure.persistence.storage import PrivateMediaStorage


class AppendOnlyQuerySet(models.QuerySet):
    """Prevent accidental mutation through bulk ORM APIs.

    Business audit records are write-once.  Django's normal model ``save``
    hooks do not run for ``QuerySet.update``/``delete``, so those paths must
    be blocked explicitly as well.
    """
    def update(self, **kwargs):
        raise RuntimeError("Append-only records cannot be updated")

    def delete(self):
        raise RuntimeError("Append-only records cannot be deleted")


class AppendOnlyManager(models.Manager.from_queryset(AppendOnlyQuerySet)):
    pass


class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("The Email field must be set")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", "general_director")
        return self.create_user(email, password, **extra_fields)


class DepartmentModel(models.Model):
    name = models.CharField(max_length=255, unique=True, verbose_name="Название отдела")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")

    class Meta:
        db_table = "departments"
        ordering = ["name"]
        verbose_name = "Отдел"
        verbose_name_plural = "Отделы"

    def __str__(self):
        return self.name


class UserModel(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True, verbose_name="Email (логин)")
    full_name = models.CharField(max_length=255, verbose_name="ФИО сотрудника")
    role = models.CharField(
        max_length=50,
        choices=[
            ("general_director", "Генеральный директор"),
            ("manager", "Руководитель"),
            ("employee", "Сотрудник"),
            ("accountant", "Бухгалтер"),
        ],
        default="employee",
        verbose_name="Роль в системе"
    )
    department = models.ForeignKey(
        DepartmentModel,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="users",
        verbose_name="Отдел"
    )
    phone = models.CharField(max_length=50, null=True, blank=True, verbose_name="Телефон")
    interface_language = models.CharField(max_length=20, default="ru", verbose_name="Язык интерфейса")
    is_active = models.BooleanField(default=True, verbose_name="Активен (не заблокирован)")
    is_staff = models.BooleanField(default=False, verbose_name="Доступ в панель управления")
    date_joined = models.DateTimeField(default=timezone.now, verbose_name="Дата регистрации")

    objects = CustomUserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["full_name"]

    class Meta:
        db_table = "users"
        ordering = ["-date_joined"]
        verbose_name = "Пользователь"
        verbose_name_plural = "Пользователи"

    def __str__(self):
        return f"{self.full_name} ({self.email})"


class BoardModel(models.Model):
    title = models.CharField(max_length=255, verbose_name="Название доски")
    department = models.ForeignKey(
        DepartmentModel,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="boards",
        verbose_name="Отдел компании"
    )
    background_theme = models.CharField(max_length=50, default="gradient-blue", verbose_name="Цветовая тема фона")
    is_archived = models.BooleanField(default=False, verbose_name="Архивирована")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")

    class Meta:
        db_table = "boards"
        ordering = ["-created_at"]
        verbose_name = "Канбан-доска"
        verbose_name_plural = "Канбан-доски"

    def __str__(self):
        return self.title


class BoardMemberModel(models.Model):
    board = models.ForeignKey(BoardModel, on_delete=models.CASCADE, related_name="members", verbose_name="Канбан-доска")
    user = models.ForeignKey(UserModel, on_delete=models.CASCADE, related_name="board_memberships", verbose_name="Сотрудник")
    role = models.CharField(max_length=50, default="employee", verbose_name="Роль на доске")  # manager, employee

    class Meta:
        db_table = "board_members"
        unique_together = ("board", "user")
        verbose_name = "Участник доски"
        verbose_name_plural = "Участники досок"

    def __str__(self):
        return f"{self.user} -> {self.board} ({self.role})"


class ColumnModel(models.Model):
    board = models.ForeignKey(BoardModel, on_delete=models.CASCADE, related_name="columns", verbose_name="Канбан-доска")
    title_ru = models.CharField(max_length=255, verbose_name="Название на русском (RU)")
    title_zh = models.CharField(max_length=255, verbose_name="Название на китайском (ZH)")
    title_ky = models.CharField(max_length=255, verbose_name="Название на кыргызском (KY)")
    original_lang = models.CharField(max_length=20, default="ru", verbose_name="Язык оригинала")
    order = models.PositiveIntegerField(default=0, verbose_name="Порядковый номер")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")

    class Meta:
        db_table = "columns"
        ordering = ["order", "created_at"]
        verbose_name = "Раздел (Колонка)"
        verbose_name_plural = "Разделы (Колонки)"

    def __str__(self):
        return f"{self.title_ru} [{self.board.title}]"


class CardModel(models.Model):
    column = models.ForeignKey(ColumnModel, on_delete=models.CASCADE, related_name="cards", verbose_name="Раздел (Колонка)")
    title_ru = models.CharField(max_length=255, verbose_name="Заголовок задачи (RU)")
    title_zh = models.CharField(max_length=255, verbose_name="Заголовок задачи (ZH)")
    title_ky = models.CharField(max_length=255, verbose_name="Заголовок задачи (KY)")
    desc_ru = models.TextField(blank=True, default="", verbose_name="Описание (RU)")
    desc_zh = models.TextField(blank=True, default="", verbose_name="Описание (ZH)")
    desc_ky = models.TextField(blank=True, default="", verbose_name="Описание (KY)")
    original_lang = models.CharField(max_length=20, default="ru", verbose_name="Язык оригинала")
    priority = models.CharField(
        max_length=20,
        choices=[
            ("low", "Низкий"),
            ("medium", "Средний"),
            ("high", "Высокий"),
            ("urgent", "Срочный"),
        ],
        default="medium",
        verbose_name="Приоритет"
    )
    due_date = models.DateTimeField(null=True, blank=True, verbose_name="Срок выполнения")
    order = models.PositiveIntegerField(default=0, verbose_name="Позиция в колонке")
    created_by = models.ForeignKey(
        UserModel,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_cards",
        verbose_name="Создатель задачи"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")

    class Meta:
        db_table = "cards"
        ordering = ["order", "-created_at"]
        verbose_name = "Карточка (Задача)"
        verbose_name_plural = "Карточки (Задачи)"

    def __str__(self):
        return self.title_ru


class CardAssigneeModel(models.Model):
    card = models.ForeignKey(CardModel, on_delete=models.CASCADE, related_name="assignee_relations", verbose_name="Задача")
    user = models.ForeignKey(UserModel, on_delete=models.CASCADE, related_name="assigned_card_relations", verbose_name="Исполнитель")

    class Meta:
        db_table = "card_assignees"
        unique_together = ("card", "user")
        verbose_name = "Назначенный исполнитель"
        verbose_name_plural = "Назначенные исполнители"

    def __str__(self):
        return f"{self.user} -> {self.card}"


class ChecklistModel(models.Model):
    card = models.ForeignKey(CardModel, on_delete=models.CASCADE, related_name="checklists", verbose_name="Задача")
    title = models.CharField(max_length=255, verbose_name="Пункт чек-листа")
    is_completed = models.BooleanField(default=False, verbose_name="Выполнено")
    order = models.PositiveIntegerField(default=0, verbose_name="Порядок")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")

    class Meta:
        db_table = "card_checklists"
        ordering = ["order", "created_at"]
        verbose_name = "Пункт чек-листа"
        verbose_name_plural = "Чек-листы"

    def __str__(self):
        return self.title


class CommentModel(models.Model):
    card = models.ForeignKey(CardModel, on_delete=models.CASCADE, related_name="comments", verbose_name="Задача")
    user = models.ForeignKey(UserModel, on_delete=models.CASCADE, related_name="card_comments", verbose_name="Автор")
    text_ru = models.TextField(verbose_name="Текст комментария (RU)")
    text_zh = models.TextField(verbose_name="Текст комментария (ZH)")
    text_ky = models.TextField(verbose_name="Текст комментария (KY)")
    original_lang = models.CharField(max_length=20, default="ru", verbose_name="Язык оригинала")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата добавления")

    class Meta:
        db_table = "card_comments"
        ordering = ["created_at"]
        verbose_name = "Комментарий"
        verbose_name_plural = "Комментарии"

    def __str__(self):
        return f"{self.user.full_name}: {self.text_ru[:40]}"


class AttachmentModel(models.Model):
    card = models.ForeignKey(CardModel, on_delete=models.CASCADE, related_name="attachments", verbose_name="Задача")
    file_path = models.CharField(max_length=500, verbose_name="URL путь к файлу")
    file_name = models.CharField(max_length=255, verbose_name="Имя файла")
    file_size = models.BigIntegerField(verbose_name="Размер (байт)")
    content_type = models.CharField(max_length=100, verbose_name="Тип файла (MIME)")
    uploaded_by = models.ForeignKey(
        UserModel,
        on_delete=models.CASCADE,
        related_name="uploaded_attachments",
        verbose_name="Кто загрузил"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата загрузки")

    class Meta:
        db_table = "card_attachments"
        ordering = ["-created_at"]
        verbose_name = "Вложение"
        verbose_name_plural = "Вложения и файлы"

    def __str__(self):
        return self.file_name


class ActivityLogModel(models.Model):
    card = models.ForeignKey(CardModel, on_delete=models.CASCADE, related_name="activity_logs", verbose_name="Задача")
    user = models.ForeignKey(UserModel, on_delete=models.CASCADE, related_name="activity_logs", verbose_name="Сотрудник")
    action_type = models.CharField(max_length=50, verbose_name="Тип действия")
    details = models.TextField(verbose_name="Детали операции")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата и время")

    class Meta:
        db_table = "card_activities"
        ordering = ["-created_at"]
        verbose_name = "Запись журнала активности"
        verbose_name_plural = "Журнал активности"

    def __str__(self):
        return f"{self.user.full_name}: {self.details}"


class NotificationModel(models.Model):
    user = models.ForeignKey(UserModel, on_delete=models.CASCADE, related_name="notifications", verbose_name="Получатель")
    title = models.CharField(max_length=255, verbose_name="Заголовок")
    message = models.TextField(verbose_name="Сообщение")
    entity_type = models.CharField(max_length=50, verbose_name="Тип сущности")
    entity_id = models.IntegerField(null=True, blank=True, verbose_name="ID сущности")
    is_read = models.BooleanField(default=False, verbose_name="Прочитано")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата отправки")

    class Meta:
        db_table = "notifications"
        ordering = ["-created_at"]
        verbose_name = "Уведомление"
        verbose_name_plural = "Уведомления"

    def __str__(self):
        return f"{self.user.email} - {self.title}"


class OfficeModel(models.Model):
    name = models.CharField(max_length=255, verbose_name="Название офиса / филиала")
    address = models.CharField(max_length=500, blank=True, default="ул. Мухаммеда Али Джиннаха, 15/1", verbose_name="Адрес офиса")
    latitude = models.FloatField(default=40.512143, verbose_name="Широта (Latitude)")
    longitude = models.FloatField(default=72.808202, verbose_name="Долгота (Longitude)")
    radius_meters = models.PositiveIntegerField(default=100, verbose_name="Радиус зоны офиса (метры)")
    ip_subnet = models.CharField(max_length=255, blank=True, default="", verbose_name="IP-подсеть или IP-адреса офиса")
    is_ip_check_enabled = models.BooleanField(default=False, verbose_name="Включить проверку IP-адреса")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата добавления")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")

    class Meta:
        db_table = "offices"
        ordering = ["name"]
        verbose_name = "Офис / Филиал"
        verbose_name_plural = "Офисы и филиалы"

    def __str__(self):
        return f"{self.name} (R={self.radius_meters}m)"


class WorkScheduleModel(models.Model):
    name = models.CharField(max_length=255, verbose_name="Название графика")
    user = models.ForeignKey(
        UserModel,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="personal_work_schedules",
        verbose_name="Сотрудник (персональный график)"
    )
    department = models.ForeignKey(
        DepartmentModel,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="department_work_schedules",
        verbose_name="Отдел (график отдела)"
    )
    start_time = models.TimeField(default="09:00:00", verbose_name="Время начала работы")
    end_time = models.TimeField(default="18:00:00", verbose_name="Время окончания работы")
    break_duration_minutes = models.PositiveIntegerField(default=60, verbose_name="Длительность обеда (минут)")
    timezone = models.CharField(max_length=100, default="Asia/Bishkek", verbose_name="Часовой пояс")
    is_active = models.BooleanField(default=True, verbose_name="Активен")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")

    class Meta:
        db_table = "work_schedules"
        ordering = ["-created_at"]
        verbose_name = "График работы"
        verbose_name_plural = "Графики работы"

    def __str__(self):
        target = self.user.full_name if self.user else (self.department.name if self.department else "Общий")
        return f"{self.name} [{target}]: {self.start_time}-{self.end_time}"


class AttendanceRecordModel(models.Model):
    user = models.ForeignKey(
        UserModel,
        on_delete=models.CASCADE,
        related_name="attendance_records",
        verbose_name="Сотрудник"
    )
    office = models.ForeignKey(
        OfficeModel,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="attendance_records",
        verbose_name="Офис"
    )
    record_type = models.CharField(
        max_length=30,
        choices=[
            ("check_in", "Пришёл"),
            ("check_out", "Ушёл"),
        ],
        verbose_name="Тип отметки"
    )
    timestamp = models.DateTimeField(default=timezone.now, verbose_name="Время отметки")
    latitude = models.FloatField(null=True, blank=True, verbose_name="Широта")
    longitude = models.FloatField(null=True, blank=True, verbose_name="Долгота")
    accuracy_meters = models.FloatField(null=True, blank=True, verbose_name="Точность GPS (метры)")
    is_within_radius = models.BooleanField(default=True, verbose_name="В радиусе офиса")
    ip_address = models.CharField(max_length=100, null=True, blank=True, verbose_name="IP-адрес")
    verification_result = models.CharField(
        max_length=50,
        choices=[
            ("verified", "Подтверждено"),
            ("rejected", "Отклонено"),
            ("manual_override", "Исправлено вручную"),
        ],
        default="verified",
        verbose_name="Результат проверки"
    )
    rejection_reason = models.TextField(blank=True, default="", verbose_name="Причина отклонения")
    is_edited = models.BooleanField(default=False, verbose_name="Исправлено вручную руководителем")
    edited_by = models.ForeignKey(
        UserModel,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="edited_attendance_records",
        verbose_name="Кто исправил"
    )
    edit_reason = models.TextField(blank=True, default="", verbose_name="Обязательная причина правки")
    original_timestamp = models.DateTimeField(null=True, blank=True, verbose_name="Исходное время до правки")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата записи")

    class Meta:
        db_table = "attendance_records"
        ordering = ["-timestamp"]
        verbose_name = "Отметка посещаемости"
        verbose_name_plural = "Отметки посещаемости"

    def __str__(self):
        return f"{self.user.full_name} - {self.record_type} ({self.timestamp.strftime('%Y-%m-%d %H:%M')})"


class AbsenceModel(models.Model):
    user = models.ForeignKey(
        UserModel,
        on_delete=models.CASCADE,
        related_name="absences",
        verbose_name="Сотрудник"
    )
    category = models.CharField(
        max_length=30,
        choices=[
            ("break", "Внутридневная отлучка"),
            ("day_status", "Статус дня"),
        ],
        default="break",
        verbose_name="Категория"
    )
    absence_type = models.CharField(
        max_length=50,
        choices=[
            ("lunch", "Обед"),
            ("business", "По делам компании"),
            ("personal", "Личное"),
            ("other", "Другое"),
            ("vacation", "Отпуск"),
            ("sick_leave", "Больничный"),
            ("business_trip", "Командировка"),
            ("day_off", "Выходной"),
        ],
        verbose_name="Тип причины"
    )
    reason = models.TextField(blank=True, default="", verbose_name="Причина")
    comment = models.TextField(blank=True, default="", verbose_name="Комментарий сотрудника")
    start_time = models.DateTimeField(default=timezone.now, verbose_name="Время начала")
    end_time = models.DateTimeField(null=True, blank=True, verbose_name="Время окончания")
    is_approved = models.BooleanField(default=True, verbose_name="Подтверждено / Одобрено")
    approved_by = models.ForeignKey(
        UserModel,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_absences",
        verbose_name="Кто подтвердил"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")

    class Meta:
        db_table = "absences"
        ordering = ["-start_time"]
        verbose_name = "Отлучка / Статус дня"
        verbose_name_plural = "Отлучки и статусы дней"

    def __str__(self):
        return f"{self.user.full_name}: {self.absence_type} ({self.start_time.strftime('%Y-%m-%d %H:%M')})"


class LocationLogModel(models.Model):
    user = models.ForeignKey(
        UserModel,
        on_delete=models.CASCADE,
        related_name="location_logs",
        verbose_name="Сотрудник"
    )
    timestamp = models.DateTimeField(default=timezone.now, verbose_name="Время геометки")
    latitude = models.FloatField(verbose_name="Широта")
    longitude = models.FloatField(verbose_name="Долгота")
    accuracy_meters = models.FloatField(null=True, blank=True, verbose_name="Точность (метры)")
    source = models.CharField(
        max_length=50,
        choices=[
            ("gps", "GPS"),
            ("network", "Network / Wi-Fi"),
            ("web", "Веб-интерфейс"),
            ("mobile", "Мобильное приложение"),
        ],
        default="gps",
        verbose_name="Источник координат"
    )
    is_outside_office = models.BooleanField(default=False, verbose_name="Вне зоны офиса")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата сохранения")

    class Meta:
        db_table = "location_logs"
        ordering = ["-timestamp"]
        verbose_name = "Геометка сотрудника"
        verbose_name_plural = "Журнал геолокаций"

    def __str__(self):
        return f"{self.user.full_name} ({self.latitude:.4f}, {self.longitude:.4f}) at {self.timestamp.strftime('%H:%M:%S')}"


class ConsentModel(models.Model):
    user = models.ForeignKey(
        UserModel,
        on_delete=models.CASCADE,
        related_name="consents",
        verbose_name="Сотрудник"
    )
    consent_version = models.CharField(max_length=50, default="1.0", verbose_name="Версия согласия")
    is_granted = models.BooleanField(default=True, verbose_name="Согласие предоставлено")
    granted_at = models.DateTimeField(default=timezone.now, verbose_name="Дата и время согласия")
    revoked_at = models.DateTimeField(null=True, blank=True, verbose_name="Дата и время отзыва")
    consent_text = models.TextField(blank=True, default="", verbose_name="Текст согласия")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата записи")

    class Meta:
        db_table = "consents"
        ordering = ["-granted_at"]
        verbose_name = "Согласие на отслеживание местоположения"
        verbose_name_plural = "Согласия сотрудников"

    def __str__(self):
        status = "Дано" if self.is_granted else "Отозвано"
        return f"{self.user.full_name} [v{self.consent_version}]: {status}"


class ExpenseModel(models.Model):
    STATUS_CHOICES = [(v, l) for v, l in [
        ("draft", "Черновик"), ("under_review", "На проверке"),
        ("needs_info", "Нужны уточнения"), ("approved", "Согласовано"),
        ("rejected", "Отклонено"), ("paid", "Выплачено"),
    ]]
    PAYMENT_SOURCE_CHOICES = [("company", "Средства компании"), ("personal", "Личные средства сотрудника")]
    PAYMENT_METHOD_CHOICES = [("corporate_card", "Корпоративная карта"), ("company_cash", "Наличные компании"), ("bank_transfer", "Банковский перевод"), ("personal_card", "Личная карта"), ("personal_cash", "Личные наличные")]
    purchase_date = models.DateField(verbose_name="Дата покупки")
    department = models.ForeignKey(DepartmentModel, on_delete=models.SET_NULL, null=True, blank=True, related_name="expenses")
    category = models.CharField(max_length=120, verbose_name="Категория")
    supplier = models.CharField(max_length=255, blank=True, default="", verbose_name="Поставщик")
    description = models.TextField(blank=True, default="", verbose_name="Описание")
    amount = models.DecimalField(max_digits=14, decimal_places=2, verbose_name="Сумма")
    currency = models.CharField(max_length=3, default="KGS", verbose_name="Валюта")
    payment_source = models.CharField(max_length=20, choices=PAYMENT_SOURCE_CHOICES, verbose_name="Источник средств")
    payment_method = models.CharField(max_length=30, choices=PAYMENT_METHOD_CHOICES, verbose_name="Способ оплаты")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")
    created_by = models.ForeignKey(UserModel, on_delete=models.PROTECT, related_name="created_expenses")
    accountant_comment = models.TextField(blank=True, default="")
    reviewed_by = models.ForeignKey(UserModel, on_delete=models.SET_NULL, null=True, blank=True, related_name="reviewed_expenses")
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "expenses"
        ordering = ["-purchase_date", "-created_at"]


class ExpenseAttachmentModel(models.Model):
    DOCUMENT_TYPES = [("kkm_receipt", "ККМ-чек"), ("bank_receipt", "Банковский чек"), ("invoice", "Счёт"), ("waybill", "Накладная"), ("other", "Другой")]
    expense = models.ForeignKey(ExpenseModel, on_delete=models.CASCADE, related_name="attachments")
    document_type = models.CharField(max_length=20, choices=DOCUMENT_TYPES, default="other")
    file = models.FileField(upload_to="expense_documents/%Y/%m/", storage=PrivateMediaStorage())
    original_name = models.CharField(max_length=255)
    file_size = models.BigIntegerField()
    uploaded_by = models.ForeignKey(UserModel, on_delete=models.PROTECT, related_name="uploaded_expense_documents")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "expense_attachments"
        ordering = ["-created_at"]


class ReimbursementPaymentModel(models.Model):
    expense = models.ForeignKey(ExpenseModel, on_delete=models.CASCADE, related_name="payments")
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    paid_at = models.DateTimeField(default=timezone.now)
    payment_method = models.CharField(max_length=50, default="bank_transfer")
    transaction_number = models.CharField(max_length=255, blank=True, default="")
    proof = models.FileField(upload_to="reimbursement_proofs/%Y/%m/", storage=PrivateMediaStorage(), null=True, blank=True)
    created_by = models.ForeignKey(UserModel, on_delete=models.PROTECT, related_name="recorded_reimbursement_payments")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "reimbursement_payments"
        ordering = ["-paid_at"]


class ExpenseActivityLogModel(models.Model):
    expense = models.ForeignKey(ExpenseModel, on_delete=models.CASCADE, related_name="activity_logs")
    user = models.ForeignKey(UserModel, on_delete=models.PROTECT)
    action = models.CharField(max_length=80)
    old_status = models.CharField(max_length=20, blank=True, default="")
    new_status = models.CharField(max_length=20, blank=True, default="")
    comment = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "expense_activity_logs"
        ordering = ["-created_at"]


# Platform RBAC deliberately stays independent from UserModel.role, which is the
# legacy Kanban role and remains the authority for board access.
class SystemPermissionModel(models.Model):
    code = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")

    class Meta:
        db_table = "system_permissions"
        ordering = ["code"]


class SystemRoleModel(models.Model):
    code = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    is_active = models.BooleanField(default=True)
    permissions = models.ManyToManyField(SystemPermissionModel, through="SystemRolePermissionModel", related_name="roles")

    class Meta:
        db_table = "system_roles"
        ordering = ["code"]


class SystemRolePermissionModel(models.Model):
    role = models.ForeignKey(SystemRoleModel, on_delete=models.CASCADE, related_name="permission_links")
    permission = models.ForeignKey(SystemPermissionModel, on_delete=models.CASCADE)

    class Meta:
        db_table = "system_role_permissions"
        constraints = [models.UniqueConstraint(fields=["role", "permission"], name="unique_system_role_permission")]


class UserSystemRoleModel(models.Model):
    user = models.ForeignKey(UserModel, on_delete=models.CASCADE, related_name="system_role_links")
    role = models.ForeignKey(SystemRoleModel, on_delete=models.CASCADE, related_name="user_links")

    class Meta:
        db_table = "user_system_roles"
        constraints = [models.UniqueConstraint(fields=["user", "role"], name="unique_user_system_role")]


class EmployeeModel(models.Model):
    STATUS_CHOICES = [("draft", "Draft"), ("pending_approval", "Pending approval"), ("active", "Active"), ("terminated", "Terminated")]
    employee_no = models.CharField(max_length=64, unique=True)
    email = models.EmailField(unique=True)
    full_name_ru = models.CharField(max_length=255)
    full_name_zh = models.CharField(max_length=255, blank=True, default="")
    full_name_ky = models.CharField(max_length=255, blank=True, default="")
    department = models.ForeignKey(DepartmentModel, on_delete=models.PROTECT, related_name="employees")
    position = models.CharField(max_length=255, blank=True, default="")
    phone = models.CharField(max_length=50, blank=True, default="")
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default="draft")
    user = models.OneToOneField(UserModel, null=True, blank=True, on_delete=models.SET_NULL, related_name="employee_profile")
    kanban_role = models.CharField(max_length=32, choices=[("manager", "Manager"), ("employee", "Employee")], default="employee")
    board = models.ForeignKey(BoardModel, null=True, blank=True, on_delete=models.SET_NULL, related_name="employee_profiles")
    hired_at = models.DateField(null=True, blank=True)
    terminated_at = models.DateField(null=True, blank=True)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "employees"
        ordering = ["employee_no"]


class MonthlyTimesheetModel(models.Model):
    """Locked, reproducible monthly attendance snapshot used by payroll."""
    employee = models.ForeignKey(EmployeeModel, on_delete=models.PROTECT, related_name="monthly_timesheets")
    year = models.PositiveSmallIntegerField(); month = models.PositiveSmallIntegerField()
    snapshot = models.JSONField(default=dict); status = models.CharField(max_length=20, choices=[("confirmed", "Confirmed")], default="confirmed")
    confirmed_by = models.ForeignKey(UserModel, on_delete=models.PROTECT, related_name="confirmed_timesheets")
    confirmed_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        db_table = "monthly_timesheets"
        constraints = [models.UniqueConstraint(fields=["employee", "year", "month"], name="unique_employee_timesheet_period")]


class ApprovalRequestModel(models.Model):
    STATUS_CHOICES = [("pending", "Pending"), ("approved", "Approved"), ("rejected", "Rejected"), ("returned", "Returned"), ("withdrawn", "Withdrawn")]
    business_type = models.CharField(max_length=64)
    business_id = models.PositiveBigIntegerField()
    applicant = models.ForeignKey(UserModel, on_delete=models.PROTECT, related_name="submitted_approvals")
    assigned_to = models.ForeignKey(UserModel, null=True, blank=True, on_delete=models.PROTECT, related_name="assigned_approvals")
    flow = models.ForeignKey("ApprovalFlowModel", null=True, blank=True, on_delete=models.PROTECT, related_name="requests")
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default="pending")
    snapshot = models.JSONField(default=dict)
    current_node = models.PositiveSmallIntegerField(default=1)
    decided_by = models.ForeignKey(UserModel, null=True, blank=True, on_delete=models.PROTECT, related_name="decided_approvals")
    decided_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "approval_requests"
        indexes = [models.Index(fields=["business_type", "business_id"]), models.Index(fields=["status", "created_at"])]


class ApprovalActionModel(models.Model):
    approval = models.ForeignKey(ApprovalRequestModel, on_delete=models.PROTECT, related_name="actions")
    actor = models.ForeignKey(UserModel, on_delete=models.PROTECT)
    action = models.CharField(max_length=32)
    comment = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "approval_actions"
        ordering = ["created_at"]

    objects = AppendOnlyManager()

    def save(self, *args, **kwargs):
        if self.pk:
            raise RuntimeError("Approval actions are append-only")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise RuntimeError("Approval actions are append-only")


class DocumentVersionModel(models.Model):
    document_type = models.CharField(max_length=64)
    document_id = models.PositiveBigIntegerField()
    version_no = models.PositiveIntegerField()
    payload = models.JSONField(default=dict)
    changed_by = models.ForeignKey(UserModel, null=True, on_delete=models.PROTECT)
    reason = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "document_versions"
        constraints = [models.UniqueConstraint(fields=["document_type", "document_id", "version_no"], name="unique_document_version")]
        ordering = ["document_type", "document_id", "version_no"]

    objects = AppendOnlyManager()

    def save(self, *args, **kwargs):
        if self.pk: raise RuntimeError("Document versions are append-only")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise RuntimeError("Document versions are append-only")


class OperationLogModel(models.Model):
    actor = models.ForeignKey(UserModel, null=True, on_delete=models.PROTECT)
    action = models.CharField(max_length=100)
    business_type = models.CharField(max_length=64)
    business_id = models.PositiveBigIntegerField()
    old_data = models.JSONField(default=dict)
    new_data = models.JSONField(default=dict)
    ip_address = models.CharField(max_length=64, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "operation_logs"
        ordering = ["-created_at"]

    objects = AppendOnlyManager()

    def save(self, *args, **kwargs):
        if self.pk: raise RuntimeError("Operation logs are append-only")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise RuntimeError("Operation logs are append-only")


class OnboardingInvitationModel(models.Model):
    """Only a hash is persisted; a browser never receives the raw token."""
    user = models.ForeignKey(UserModel, on_delete=models.CASCADE, related_name="onboarding_invitations")
    token_hash = models.CharField(max_length=128, unique=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(UserModel, on_delete=models.PROTECT, related_name="created_onboarding_invitations")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "onboarding_invitations"
        ordering = ["-created_at"]


class ApprovalFlowModel(models.Model):
    business_type = models.CharField(max_length=64, unique=True)
    name = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    class Meta: db_table = "approval_flows"


class ApprovalNodeModel(models.Model):
    flow = models.ForeignKey(ApprovalFlowModel, on_delete=models.CASCADE, related_name="nodes")
    order = models.PositiveSmallIntegerField()
    approver_type = models.CharField(max_length=32, choices=[("user", "User"), ("role", "Role"), ("department_leader", "Department leader")])
    user = models.ForeignKey(UserModel, null=True, blank=True, on_delete=models.PROTECT)
    role = models.ForeignKey(SystemRoleModel, null=True, blank=True, on_delete=models.PROTECT)
    class Meta:
        db_table = "approval_nodes"
        constraints = [models.UniqueConstraint(fields=["flow", "order"], name="unique_approval_node_order")]


class EmailOutboxModel(models.Model):
    """Delivery state only.  Invitation secrets are never persisted here."""
    to_email = models.EmailField(); subject = models.CharField(max_length=255); body = models.TextField()
    invitation = models.OneToOneField(OnboardingInvitationModel, null=True, blank=True, on_delete=models.SET_NULL, related_name="outbox")
    status = models.CharField(max_length=20, default="pending")
    attempts = models.PositiveSmallIntegerField(default=0); last_error = models.TextField(blank=True, default="")
    sent_at = models.DateTimeField(null=True, blank=True); created_at = models.DateTimeField(auto_now_add=True)
    class Meta: db_table = "email_outbox"


# Phase 2 — procurement master data.  Financial liabilities are deliberately
# not created here: they arise only after the WMS receiving/reconciliation flow.
class SupplierModel(models.Model):
    STATUS = [("draft", "Draft"), ("pending_approval", "Pending approval"), ("active", "Active"), ("blocked", "Blocked")]
    name_ru = models.CharField(max_length=255)
    name_zh = models.CharField(max_length=255, blank=True, default="")
    name_ky = models.CharField(max_length=255, blank=True, default="")
    country = models.CharField(max_length=80, blank=True, default="")
    contact = models.CharField(max_length=255, blank=True, default="")
    phone = models.CharField(max_length=64, blank=True, default="")
    tax_no = models.CharField(max_length=128, blank=True, default="")
    currency = models.CharField(max_length=3, default="KGS")
    status = models.CharField(max_length=32, choices=STATUS, default="draft")
    created_by = models.ForeignKey(UserModel, on_delete=models.PROTECT, related_name="created_suppliers")
    created_at = models.DateTimeField(auto_now_add=True); updated_at = models.DateTimeField(auto_now=True)
    class Meta: db_table = "suppliers"; ordering = ["name_ru"]


class GoodsCategoryModel(models.Model):
    parent = models.ForeignKey("self", null=True, blank=True, on_delete=models.PROTECT, related_name="children")
    name_ru = models.CharField(max_length=255); name_zh = models.CharField(max_length=255, blank=True, default=""); name_ky = models.CharField(max_length=255, blank=True, default="")
    sort = models.PositiveIntegerField(default=0)
    class Meta: db_table = "goods_categories"; ordering = ["sort", "name_ru"]


class GoodsSKUModel(models.Model):
    STATUS = [("draft", "Draft"), ("pending_approval", "Pending approval"), ("active", "Active"), ("discontinued", "Discontinued")]
    sku_code = models.CharField(max_length=64, unique=True); barcode = models.CharField(max_length=128, blank=True, default="", db_index=True)
    name_ru = models.CharField(max_length=255); name_zh = models.CharField(max_length=255, blank=True, default=""); name_ky = models.CharField(max_length=255, blank=True, default="")
    category = models.ForeignKey(GoodsCategoryModel, null=True, blank=True, on_delete=models.PROTECT)
    brand = models.CharField(max_length=128, blank=True, default=""); origin = models.CharField(max_length=128, blank=True, default="")
    shelf_life_days = models.PositiveIntegerField(null=True, blank=True); status = models.CharField(max_length=32, choices=STATUS, default="draft")
    created_by = models.ForeignKey(UserModel, on_delete=models.PROTECT, related_name="created_skus"); created_at = models.DateTimeField(auto_now_add=True); updated_at = models.DateTimeField(auto_now=True)
    class Meta: db_table = "goods_skus"; ordering = ["sku_code"]


class SupplierQuoteModel(models.Model):
    supplier = models.ForeignKey(SupplierModel, on_delete=models.PROTECT, related_name="quotes"); sku = models.ForeignKey(GoodsSKUModel, on_delete=models.PROTECT, related_name="supplier_quotes")
    price = models.DecimalField(max_digits=14, decimal_places=2); currency = models.CharField(max_length=3, default="KGS"); moq = models.PositiveIntegerField(default=1); delivery_days = models.PositiveIntegerField(default=0)
    valid_from = models.DateField(null=True, blank=True); valid_until = models.DateField(null=True, blank=True); created_at = models.DateTimeField(auto_now_add=True)
    class Meta: db_table = "supplier_quotes"; constraints = [models.UniqueConstraint(fields=["supplier", "sku", "currency"], name="unique_supplier_sku_currency_quote")]


class PurchaseOrderModel(models.Model):
    """Approved supplier order; stock/financial posting is deferred to WMS."""
    STATUS = [("draft", "Draft"), ("pending_approval", "Pending approval"), ("approved", "Approved"), ("partially_received", "Partially received"), ("received", "Received"), ("closed", "Closed"), ("cancelled", "Cancelled")]
    po_no = models.CharField(max_length=64, unique=True)
    supplier = models.ForeignKey(SupplierModel, on_delete=models.PROTECT, related_name="purchase_orders")
    department = models.ForeignKey(DepartmentModel, null=True, blank=True, on_delete=models.PROTECT)
    order_date = models.DateField(); expected_delivery_date = models.DateField(null=True, blank=True)
    currency = models.CharField(max_length=3, default="KGS"); status = models.CharField(max_length=32, choices=STATUS, default="draft")
    created_by = models.ForeignKey(UserModel, on_delete=models.PROTECT, related_name="created_purchase_orders")
    created_at = models.DateTimeField(auto_now_add=True); updated_at = models.DateTimeField(auto_now=True)
    class Meta: db_table = "purchase_orders"; ordering = ["-created_at"]


class PurchaseOrderItemModel(models.Model):
    purchase_order = models.ForeignKey(PurchaseOrderModel, on_delete=models.CASCADE, related_name="items")
    sku = models.ForeignKey(GoodsSKUModel, on_delete=models.PROTECT)
    ordered_qty = models.PositiveIntegerField(); received_qty = models.PositiveIntegerField(default=0)
    unit_price = models.DecimalField(max_digits=14, decimal_places=2)
    class Meta:
        db_table = "purchase_order_items"
        constraints = [models.UniqueConstraint(fields=["purchase_order", "sku"], name="unique_po_sku")]


class WarehouseModel(models.Model):
    name_ru = models.CharField(max_length=255); name_zh = models.CharField(max_length=255, blank=True, default=""); name_ky = models.CharField(max_length=255, blank=True, default="")
    address = models.CharField(max_length=500, blank=True, default=""); manager = models.ForeignKey(UserModel, null=True, blank=True, on_delete=models.PROTECT)
    class Meta: db_table = "warehouses"


class WarehouseLocationModel(models.Model):
    warehouse = models.ForeignKey(WarehouseModel, on_delete=models.CASCADE, related_name="locations"); code = models.CharField(max_length=64)
    class Meta: db_table = "warehouse_locations"; constraints = [models.UniqueConstraint(fields=["warehouse", "code"], name="unique_warehouse_location")]


class StockInventoryModel(models.Model):
    warehouse = models.ForeignKey(WarehouseModel, on_delete=models.PROTECT); location = models.ForeignKey(WarehouseLocationModel, null=True, blank=True, on_delete=models.PROTECT); sku = models.ForeignKey(GoodsSKUModel, on_delete=models.PROTECT)
    qty = models.DecimalField(max_digits=14, decimal_places=3, default=0); avg_cost = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    class Meta: db_table = "stock_inventory"; constraints = [models.UniqueConstraint(fields=["warehouse", "location", "sku"], name="unique_stock_balance")]


class StockMovementModel(models.Model):
    """Append-only stock ledger; balances change only through posted movements."""
    TYPES = [("receipt", "Receipt"), ("issue", "Issue"), ("transfer_out", "Transfer out"), ("transfer_in", "Transfer in"), ("adjustment", "Adjustment")]
    warehouse = models.ForeignKey(WarehouseModel, on_delete=models.PROTECT); location = models.ForeignKey(WarehouseLocationModel, null=True, blank=True, on_delete=models.PROTECT)
    sku = models.ForeignKey(GoodsSKUModel, on_delete=models.PROTECT); qty_delta = models.DecimalField(max_digits=14, decimal_places=3); unit_cost = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    movement_type = models.CharField(max_length=32, choices=TYPES); source_type = models.CharField(max_length=64); source_id = models.PositiveBigIntegerField(); reason = models.TextField(blank=True, default="")
    posted_by = models.ForeignKey(UserModel, on_delete=models.PROTECT); posted_at = models.DateTimeField(auto_now_add=True)
    class Meta: db_table = "stock_movements"; ordering = ["-posted_at"]


class PurchaseReceiptModel(models.Model):
    STATUS = [("draft", "Draft"), ("posted", "Posted"), ("cancelled", "Cancelled")]
    receipt_no = models.CharField(max_length=64, unique=True); purchase_order = models.ForeignKey(PurchaseOrderModel, on_delete=models.PROTECT, related_name="receipts")
    warehouse = models.ForeignKey(WarehouseModel, on_delete=models.PROTECT); status = models.CharField(max_length=20, choices=STATUS, default="draft")
    received_by = models.ForeignKey(UserModel, on_delete=models.PROTECT); received_at = models.DateTimeField(auto_now_add=True); comment = models.TextField(blank=True, default="")
    class Meta: db_table = "purchase_receipts"


class PurchaseReceiptItemModel(models.Model):
    receipt = models.ForeignKey(PurchaseReceiptModel, on_delete=models.CASCADE, related_name="items"); po_item = models.ForeignKey(PurchaseOrderItemModel, on_delete=models.PROTECT)
    location = models.ForeignKey(WarehouseLocationModel, null=True, blank=True, on_delete=models.PROTECT); qty = models.PositiveIntegerField(); unit_cost = models.DecimalField(max_digits=14, decimal_places=2)
    batch_no = models.CharField(max_length=128, blank=True, default=""); expiry_date = models.DateField(null=True, blank=True)
    discrepancy_reason = models.TextField(blank=True, default="")
    class Meta: db_table = "purchase_receipt_items"


class StockTransferModel(models.Model):
    STATUS = [("draft", "Draft"), ("pending_approval", "Pending approval"), ("approved", "Approved"), ("in_transit", "In transit"), ("received", "Received"), ("rejected", "Rejected"), ("cancelled", "Cancelled")]
    transfer_no = models.CharField(max_length=64, unique=True)
    source_warehouse = models.ForeignKey(WarehouseModel, on_delete=models.PROTECT, related_name="outgoing_transfers")
    destination_warehouse = models.ForeignKey(WarehouseModel, on_delete=models.PROTECT, related_name="incoming_transfers")
    status = models.CharField(max_length=20, choices=STATUS, default="draft")
    created_by = models.ForeignKey(UserModel, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    comment = models.TextField(blank=True, default="")
    review_comment = models.TextField(blank=True, default="")
    approved_by = models.ForeignKey(UserModel, null=True, blank=True, on_delete=models.PROTECT, related_name="approved_stock_transfers")
    approved_at = models.DateTimeField(null=True, blank=True)
    dispatched_by = models.ForeignKey(UserModel, null=True, blank=True, on_delete=models.PROTECT, related_name="dispatched_stock_transfers")
    dispatched_at = models.DateTimeField(null=True, blank=True)
    received_by = models.ForeignKey(UserModel, null=True, blank=True, on_delete=models.PROTECT, related_name="received_stock_transfers")
    received_at = models.DateTimeField(null=True, blank=True)
    class Meta: db_table = "stock_transfers"


class StockTransferItemModel(models.Model):
    transfer = models.ForeignKey(StockTransferModel, on_delete=models.CASCADE, related_name="items")
    sku = models.ForeignKey(GoodsSKUModel, on_delete=models.PROTECT)
    qty = models.PositiveIntegerField()
    source_location = models.ForeignKey(WarehouseLocationModel, null=True, blank=True, on_delete=models.PROTECT, related_name="outgoing_transfer_items")
    destination_location = models.ForeignKey(WarehouseLocationModel, null=True, blank=True, on_delete=models.PROTECT, related_name="incoming_transfer_items")
    batch_no = models.CharField(max_length=128, blank=True, default="")
    expiry_date = models.DateField(null=True, blank=True)
    unit_cost = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    class Meta: db_table = "stock_transfer_items"; constraints = [models.UniqueConstraint(fields=["transfer", "sku"], name="unique_transfer_sku")]


class StockBatchModel(models.Model):
    inventory = models.ForeignKey(StockInventoryModel, on_delete=models.CASCADE, related_name="batches"); batch_no = models.CharField(max_length=128); expiry_date = models.DateField(); qty = models.DecimalField(max_digits=14, decimal_places=3)
    class Meta: db_table = "stock_batches"; constraints = [models.UniqueConstraint(fields=["inventory", "batch_no"], name="unique_inventory_batch")]


class StockCountModel(models.Model):
    STATUS = [("draft", "Draft"), ("counted", "Counted"), ("approved", "Approved")]
    count_no = models.CharField(max_length=64, unique=True); warehouse = models.ForeignKey(WarehouseModel, on_delete=models.PROTECT); status = models.CharField(max_length=16, choices=STATUS, default="draft"); created_by = models.ForeignKey(UserModel, on_delete=models.PROTECT); created_at = models.DateTimeField(auto_now_add=True)
    class Meta: db_table = "stock_counts"


class StockCountItemModel(models.Model):
    count = models.ForeignKey(StockCountModel, on_delete=models.CASCADE, related_name="items"); sku = models.ForeignKey(GoodsSKUModel, on_delete=models.PROTECT); system_qty = models.DecimalField(max_digits=14, decimal_places=3); actual_qty = models.DecimalField(max_digits=14, decimal_places=3); reason = models.TextField(blank=True, default="")
    class Meta: db_table = "stock_count_items"; constraints = [models.UniqueConstraint(fields=["count", "sku"], name="unique_count_sku")]


class FinanceAccountModel(models.Model):
    name = models.CharField(max_length=255); bank_name = models.CharField(max_length=255, blank=True, default=""); currency = models.CharField(max_length=3); balance = models.DecimalField(max_digits=16, decimal_places=2, default=0); is_active = models.BooleanField(default=True)
    class Meta: db_table = "finance_accounts"; constraints = [models.UniqueConstraint(fields=["name", "currency"], name="unique_finance_account_currency")]


class FinancePayableModel(models.Model):
    STATUS = [("open", "Open"), ("partially_paid", "Partially paid"), ("paid", "Paid"), ("cancelled", "Cancelled")]
    supplier = models.ForeignKey(SupplierModel, on_delete=models.PROTECT); purchase_order = models.ForeignKey(PurchaseOrderModel, null=True, blank=True, on_delete=models.PROTECT)
    source_type = models.CharField(max_length=64); source_id = models.PositiveBigIntegerField(); amount = models.DecimalField(max_digits=16, decimal_places=2); outstanding_amount = models.DecimalField(max_digits=16, decimal_places=2); currency = models.CharField(max_length=3); due_date = models.DateField(null=True, blank=True); status = models.CharField(max_length=20, choices=STATUS, default="open"); created_at = models.DateTimeField(auto_now_add=True)
    class Meta: db_table = "finance_payables"; constraints = [models.UniqueConstraint(fields=["source_type", "source_id"], name="unique_payable_source")]


class FinancePaymentModel(models.Model):
    payable = models.ForeignKey(FinancePayableModel, on_delete=models.PROTECT, related_name="payments"); account = models.ForeignKey(FinanceAccountModel, on_delete=models.PROTECT); amount = models.DecimalField(max_digits=16, decimal_places=2); payment_date = models.DateField(); transaction_no = models.CharField(max_length=128); proof_file = models.CharField(max_length=500, blank=True, default=""); created_by = models.ForeignKey(UserModel, on_delete=models.PROTECT); created_at = models.DateTimeField(auto_now_add=True)
    class Meta: db_table = "finance_payments"; constraints = [models.UniqueConstraint(fields=["account", "transaction_no"], name="unique_payment_transaction")]


class FinanceFxRateModel(models.Model):
    base_currency = models.CharField(max_length=3); quote_currency = models.CharField(max_length=3); rate = models.DecimalField(max_digits=18, decimal_places=8); valid_at = models.DateField(); changed_by = models.ForeignKey(UserModel, on_delete=models.PROTECT); created_at = models.DateTimeField(auto_now_add=True)
    class Meta: db_table = "finance_fx_rates"; constraints = [models.UniqueConstraint(fields=["base_currency", "quote_currency", "valid_at"], name="unique_fx_rate_day")]


class FinancePeriodModel(models.Model):
    year = models.PositiveSmallIntegerField(); month = models.PositiveSmallIntegerField(); is_closed = models.BooleanField(default=False); closed_by = models.ForeignKey(UserModel, null=True, blank=True, on_delete=models.PROTECT); closed_at = models.DateTimeField(null=True, blank=True)
    class Meta: db_table = "finance_periods"; constraints = [models.UniqueConstraint(fields=["year", "month"], name="unique_finance_period")]


class SupplierStatementModel(models.Model):
    STATUS = [("draft", "Draft"), ("confirmed", "Confirmed"), ("cancelled", "Cancelled")]
    statement_no = models.CharField(max_length=64, unique=True); supplier = models.ForeignKey(SupplierModel, on_delete=models.PROTECT); purchase_order = models.ForeignKey(PurchaseOrderModel, on_delete=models.PROTECT)
    period_start = models.DateField(); period_end = models.DateField(); total_amount = models.DecimalField(max_digits=16, decimal_places=2); currency = models.CharField(max_length=3); status = models.CharField(max_length=20, choices=STATUS, default="draft"); confirmed_by = models.ForeignKey(UserModel, null=True, blank=True, on_delete=models.PROTECT); confirmed_at = models.DateTimeField(null=True, blank=True); created_by = models.ForeignKey(UserModel, on_delete=models.PROTECT, related_name="created_supplier_statements"); created_at = models.DateTimeField(auto_now_add=True)
    class Meta: db_table = "supplier_statements"; constraints = [models.UniqueConstraint(fields=["purchase_order", "period_start", "period_end"], name="unique_statement_period")]


class GoodsCertificateModel(models.Model):
    sku = models.ForeignKey(GoodsSKUModel, on_delete=models.CASCADE, related_name="certificates"); number = models.CharField(max_length=128); file_path = models.CharField(max_length=500); expires_at = models.DateField(); created_by = models.ForeignKey(UserModel, on_delete=models.PROTECT); created_at = models.DateTimeField(auto_now_add=True)
    class Meta: db_table = "goods_certificates"; constraints = [models.UniqueConstraint(fields=["sku", "number"], name="unique_sku_certificate")]
class GoodsPriceHistoryModel(models.Model):
    sku = models.ForeignKey(GoodsSKUModel, on_delete=models.PROTECT, related_name="price_history"); price_type = models.CharField(max_length=32); currency = models.CharField(max_length=3); old_price = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True); new_price = models.DecimalField(max_digits=14, decimal_places=2); effective_at = models.DateTimeField(); changed_by = models.ForeignKey(UserModel, on_delete=models.PROTECT); approval_id = models.PositiveBigIntegerField(null=True, blank=True)
    class Meta: db_table = "goods_price_history"; ordering = ["-effective_at"]


class KpiTemplateModel(models.Model):
    name = models.CharField(max_length=255); position_code = models.CharField(max_length=128); cycle = models.CharField(max_length=16, choices=[("month", "Month"), ("quarter", "Quarter"), ("year", "Year")]); is_active = models.BooleanField(default=True)
    class Meta: db_table = "kpi_templates"


class KpiTemplateItemModel(models.Model):
    template = models.ForeignKey(KpiTemplateModel, on_delete=models.CASCADE, related_name="items"); name_ru = models.CharField(max_length=255); name_zh = models.CharField(max_length=255, blank=True, default=""); name_ky = models.CharField(max_length=255, blank=True, default=""); weight = models.DecimalField(max_digits=5, decimal_places=2); formula = models.TextField(blank=True, default="")
    class Meta: db_table = "kpi_template_items"


class KpiTaskModel(models.Model):
    STATUS = [("self_review", "Self review"), ("manager_review", "Manager review"), ("senior_review", "Senior review"), ("confirmed", "Confirmed")]
    template = models.ForeignKey(KpiTemplateModel, on_delete=models.PROTECT); employee = models.ForeignKey(EmployeeModel, on_delete=models.PROTECT); year = models.PositiveSmallIntegerField(); period = models.CharField(max_length=16); self_score = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True); manager_score = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True); final_score = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True); status = models.CharField(max_length=20, choices=STATUS, default="self_review")
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    manager_scored_by = models.ForeignKey(UserModel, null=True, blank=True, on_delete=models.PROTECT, related_name="managed_kpi_tasks")
    reviewed_by = models.ForeignKey(UserModel, null=True, blank=True, on_delete=models.PROTECT, related_name="reviewed_kpi_tasks")
    reviewed_at = models.DateTimeField(null=True, blank=True)
    archived_at = models.DateTimeField(null=True, blank=True)
    comments = models.JSONField(default=dict, blank=True)
    class Meta: db_table = "kpi_tasks"; constraints = [models.UniqueConstraint(fields=["template", "employee", "year", "period"], name="unique_kpi_task_period")]


class AdminAssetModel(models.Model):
    STATUS = [("in_use", "In use"), ("repair", "Repair"), ("written_off", "Written off")]
    asset_no = models.CharField(max_length=64, unique=True); name = models.CharField(max_length=255); category = models.CharField(max_length=128); purchase_date = models.DateField(null=True, blank=True); price = models.DecimalField(max_digits=14, decimal_places=2, default=0); owner = models.ForeignKey(EmployeeModel, null=True, blank=True, on_delete=models.PROTECT); status = models.CharField(max_length=20, choices=STATUS, default="in_use")
    class Meta: db_table = "admin_assets"

class AdminAssetLogModel(models.Model):
    asset=models.ForeignKey(AdminAssetModel,on_delete=models.PROTECT,related_name="logs");employee=models.ForeignKey(EmployeeModel,on_delete=models.PROTECT);operation=models.CharField(max_length=16,choices=[("issued","Issued"),("returned","Returned")]);performed_by=models.ForeignKey(UserModel,on_delete=models.PROTECT);created_at=models.DateTimeField(auto_now_add=True);comment=models.TextField(blank=True,default="")
    class Meta:db_table="admin_asset_logs";ordering=["-created_at"]

class EmployeeFileModel(models.Model):
    employee=models.ForeignKey(EmployeeModel,on_delete=models.CASCADE,related_name="files");file_name=models.CharField(max_length=255);file_path=models.CharField(max_length=500);file_type=models.CharField(max_length=64);expires_at=models.DateField(null=True,blank=True);version_no=models.PositiveIntegerField(default=1);uploaded_by=models.ForeignKey(UserModel,on_delete=models.PROTECT);created_at=models.DateTimeField(auto_now_add=True)
    class Meta:db_table="employee_files";constraints=[models.UniqueConstraint(fields=["employee","file_name","version_no"],name="unique_employee_file_version")]

class EmployeeChangeModel(models.Model):
    employee=models.ForeignKey(EmployeeModel,on_delete=models.PROTECT,related_name="changes");change_type=models.CharField(max_length=64);before_data=models.JSONField(default=dict);after_data=models.JSONField(default=dict);approval_id=models.PositiveBigIntegerField(null=True,blank=True);created_by=models.ForeignKey(UserModel,on_delete=models.PROTECT);created_at=models.DateTimeField(auto_now_add=True)
    class Meta:db_table="employee_changes";ordering=["-created_at"]


class AdminNoticeModel(models.Model):
    title_ru = models.CharField(max_length=255); title_zh = models.CharField(max_length=255, blank=True, default=""); title_ky = models.CharField(max_length=255, blank=True, default=""); content_ru = models.TextField(); content_zh = models.TextField(blank=True, default=""); content_ky = models.TextField(blank=True, default=""); published_by = models.ForeignKey(UserModel, on_delete=models.PROTECT); published_at = models.DateTimeField(auto_now_add=True); is_top = models.BooleanField(default=False)
    class Meta: db_table = "admin_notices"


class FinanceSalaryModel(models.Model):
    STATUS = [("draft", "Draft"), ("approved", "Approved"), ("paid", "Paid")]
    employee = models.ForeignKey(EmployeeModel, on_delete=models.PROTECT); year = models.PositiveSmallIntegerField(); month = models.PositiveSmallIntegerField()
    base_salary = models.DecimalField(max_digits=16, decimal_places=2); attendance_deduction = models.DecimalField(max_digits=16, decimal_places=2, default=0); kpi_bonus = models.DecimalField(max_digits=16, decimal_places=2, default=0); other_adjustment = models.DecimalField(max_digits=16, decimal_places=2, default=0); total_pay = models.DecimalField(max_digits=16, decimal_places=2); currency = models.CharField(max_length=3, default="KGS"); status = models.CharField(max_length=20, choices=STATUS, default="draft"); created_by = models.ForeignKey(UserModel, on_delete=models.PROTECT); created_at = models.DateTimeField(auto_now_add=True)
    class Meta: db_table = "finance_salaries"; constraints = [models.UniqueConstraint(fields=["employee", "year", "month"], name="unique_salary_period")]


class AdminSupplyModel(models.Model):
    name = models.CharField(max_length=255); unit = models.CharField(max_length=32); stock_qty = models.DecimalField(max_digits=14, decimal_places=3, default=0)
    class Meta: db_table = "admin_supplies"
class AdminSupplyRequestModel(models.Model):
    STATUS=[("draft","Draft"),("pending","Pending"),("approved","Approved"),("rejected","Rejected")]
    supply=models.ForeignKey(AdminSupplyModel,on_delete=models.PROTECT); requester=models.ForeignKey(UserModel,on_delete=models.PROTECT); qty=models.DecimalField(max_digits=14,decimal_places=3);status=models.CharField(max_length=20,choices=STATUS,default="draft");comment=models.TextField(blank=True,default="");created_at=models.DateTimeField(auto_now_add=True)
    class Meta:db_table="admin_supply_requests"
class AdminCarModel(models.Model):
    plate_no=models.CharField(max_length=32,unique=True);model=models.CharField(max_length=128);is_active=models.BooleanField(default=True)
    class Meta:db_table="admin_cars"
class AdminCarRequestModel(models.Model):
    STATUS=[("draft","Draft"),("pending","Pending"),("approved","Approved"),("rejected","Rejected")]
    car=models.ForeignKey(AdminCarModel,on_delete=models.PROTECT);requester=models.ForeignKey(UserModel,on_delete=models.PROTECT);start_at=models.DateTimeField();end_at=models.DateTimeField();destination=models.CharField(max_length=255);mileage=models.DecimalField(max_digits=12,decimal_places=1,default=0);status=models.CharField(max_length=20,choices=STATUS,default="draft")
    class Meta:db_table="admin_car_requests"
class AdminMeetingRoomModel(models.Model):
    name=models.CharField(max_length=128,unique=True);capacity=models.PositiveIntegerField(default=1);is_active=models.BooleanField(default=True)
    class Meta:db_table="admin_meeting_rooms"
class AdminMeetingBookingModel(models.Model):
    STATUS=[("booked","Booked"),("cancelled","Cancelled")]
    room=models.ForeignKey(AdminMeetingRoomModel,on_delete=models.PROTECT);requester=models.ForeignKey(UserModel,on_delete=models.PROTECT);start_at=models.DateTimeField();end_at=models.DateTimeField();status=models.CharField(max_length=20,choices=STATUS,default="booked")
    class Meta:db_table="admin_meeting_bookings"
class AdminSealRequestModel(models.Model):
    STATUS=[("draft","Draft"),("pending","Pending"),("approved","Approved"),("rejected","Rejected")]
    requester=models.ForeignKey(UserModel,on_delete=models.PROTECT);reason=models.TextField();document_path=models.CharField(max_length=500);status=models.CharField(max_length=20,choices=STATUS,default="draft");created_at=models.DateTimeField(auto_now_add=True)
    class Meta:db_table="admin_seal_requests"
class AdminLicenseModel(models.Model):
    license_type=models.CharField(max_length=128);file_path=models.CharField(max_length=500);issue_date=models.DateField();expiry_date=models.DateField();owner_department=models.ForeignKey(DepartmentModel,on_delete=models.PROTECT);created_by=models.ForeignKey(UserModel,on_delete=models.PROTECT);created_at=models.DateTimeField(auto_now_add=True)
    class Meta:db_table="admin_licenses"



class StockWriteoffModel(models.Model):
    STATUS = [("draft", "Draft"), ("pending_approval", "Pending approval"), ("approved", "Approved"), ("posted", "Posted"), ("rejected", "Rejected"), ("cancelled", "Cancelled")]
    writeoff_no = models.CharField(max_length=64, unique=True)
    warehouse = models.ForeignKey(WarehouseModel, on_delete=models.PROTECT)
    reason = models.TextField()
    status = models.CharField(max_length=24, choices=STATUS, default="draft")
    created_by = models.ForeignKey(UserModel, on_delete=models.PROTECT, related_name="created_stock_writeoffs")
    created_at = models.DateTimeField(auto_now_add=True)
    approved_by = models.ForeignKey(UserModel, null=True, blank=True, on_delete=models.PROTECT, related_name="approved_stock_writeoffs")
    approved_at = models.DateTimeField(null=True, blank=True)
    posted_by = models.ForeignKey(UserModel, null=True, blank=True, on_delete=models.PROTECT, related_name="posted_stock_writeoffs")
    posted_at = models.DateTimeField(null=True, blank=True)
    review_comment = models.TextField(blank=True, default="")

    class Meta:
        db_table = "stock_writeoffs"


class StockWriteoffItemModel(models.Model):
    writeoff = models.ForeignKey(StockWriteoffModel, on_delete=models.CASCADE, related_name="items")
    sku = models.ForeignKey(GoodsSKUModel, on_delete=models.PROTECT)
    location = models.ForeignKey(WarehouseLocationModel, null=True, blank=True, on_delete=models.PROTECT)
    qty = models.DecimalField(max_digits=14, decimal_places=3)
    batch_no = models.CharField(max_length=128, blank=True, default="")
    expiry_date = models.DateField(null=True, blank=True)
    unit_cost = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)

    class Meta:
        db_table = "stock_writeoff_items"
        constraints = [
            models.UniqueConstraint(fields=["writeoff", "sku", "location", "batch_no"], name="unique_writeoff_sku_location_batch"),
            models.CheckConstraint(condition=models.Q(qty__gt=0), name="writeoff_positive_qty"),
            models.CheckConstraint(condition=models.Q(unit_cost__gte=0) | models.Q(unit_cost__isnull=True), name="writeoff_nonnegative_cost"),
        ]


class StockWriteoffPhotoModel(models.Model):
    writeoff = models.ForeignKey(StockWriteoffModel, on_delete=models.PROTECT, related_name="photos")
    file_path = models.CharField(max_length=255)
    file_name = models.CharField(max_length=255)
    content_type = models.CharField(max_length=32)
    size = models.PositiveIntegerField()
    is_active = models.BooleanField(default=True)
    uploaded_by = models.ForeignKey(UserModel, on_delete=models.PROTECT)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "stock_writeoff_photos"
