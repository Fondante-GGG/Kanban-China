from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils import timezone


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
    address = models.CharField(max_length=500, blank=True, default="", verbose_name="Адрес офиса")
    latitude = models.FloatField(default=42.8746, verbose_name="Широта (Latitude)")
    longitude = models.FloatField(default=74.5698, verbose_name="Долгота (Longitude)")
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

