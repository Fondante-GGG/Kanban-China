from django.contrib import admin
from backend.infrastructure.persistence.models import (
    DepartmentModel, UserModel, BoardModel, BoardMemberModel, ColumnModel,
    CardModel, CardAssigneeModel, ChecklistModel, CommentModel, AttachmentModel,
    ActivityLogModel, NotificationModel,
    OfficeModel, WorkScheduleModel, AttendanceRecordModel, AbsenceModel,
    LocationLogModel, ConsentModel
    , ExpenseModel, ExpenseAttachmentModel, ReimbursementPaymentModel, ExpenseActivityLogModel
)


@admin.register(DepartmentModel)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "get_boards_count", "get_users_count", "created_at")
    search_fields = ("name",)
    ordering = ("name",)

    def get_boards_count(self, obj):
        return obj.boards.count()
    get_boards_count.short_description = "Число досок"

    def get_users_count(self, obj):
        return obj.users.count()
    get_users_count.short_description = "Число сотрудников"


class BoardMemberInline(admin.TabularInline):
    model = BoardMemberModel
    verbose_name = "Участник доски"
    verbose_name_plural = "Участники доски"
    extra = 1


class ColumnInline(admin.TabularInline):
    model = ColumnModel
    verbose_name = "Раздел (Колонка)"
    verbose_name_plural = "Разделы (Колонки)"
    extra = 0
    fields = ("title_ru", "title_zh", "title_ky", "order")


@admin.register(BoardModel)
class BoardAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "department", "background_theme", "is_archived", "get_columns_count", "created_at")
    list_filter = ("department", "background_theme", "is_archived")
    search_fields = ("title", "department__name")
    inlines = [BoardMemberInline, ColumnInline]

    def get_columns_count(self, obj):
        return obj.columns.count()
    get_columns_count.short_description = "Число разделов"


@admin.register(UserModel)
class UserAdmin(admin.ModelAdmin):
    list_display = ("id", "email", "full_name", "role", "department", "phone", "is_active", "date_joined")
    list_filter = ("role", "department", "is_active")
    search_fields = ("email", "full_name", "phone")
    ordering = ("-date_joined",)
    fieldsets = (
        ("Учётные данные", {"fields": ("email", "password")}),
        ("Личные данные", {"fields": ("full_name", "phone", "role", "department", "interface_language")}),
        ("Права и статус", {"fields": ("is_active", "is_staff", "is_superuser")}),
    )


class ChecklistInline(admin.TabularInline):
    model = ChecklistModel
    verbose_name = "Пункт чек-листа"
    verbose_name_plural = "Чек-лист задачи"
    extra = 1


class CommentInline(admin.StackedInline):
    model = CommentModel
    verbose_name = "Комментарий"
    verbose_name_plural = "Комментарии"
    extra = 0
    readonly_fields = ("created_at",)


class CardAssigneeInline(admin.TabularInline):
    model = CardAssigneeModel
    verbose_name = "Исполнитель задачи"
    verbose_name_plural = "Назначенные исполнители"
    extra = 1


@admin.register(CardModel)
class CardAdmin(admin.ModelAdmin):
    list_display = ("id", "title_ru", "column", "priority", "due_date", "created_by", "created_at")
    list_filter = ("priority", "column__board", "created_at")
    search_fields = ("title_ru", "title_zh", "title_ky", "desc_ru")
    inlines = [CardAssigneeInline, ChecklistInline, CommentInline]


@admin.register(ColumnModel)
class ColumnAdmin(admin.ModelAdmin):
    list_display = ("id", "title_ru", "title_zh", "title_ky", "board", "order", "created_at")
    list_filter = ("board",)
    search_fields = ("title_ru", "title_zh", "title_ky")
    ordering = ("board", "order")


@admin.register(CommentModel)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("id", "card", "user", "text_ru", "created_at")
    search_fields = ("text_ru", "text_zh", "text_ky", "user__full_name")
    list_filter = ("created_at",)


@admin.register(AttachmentModel)
class AttachmentAdmin(admin.ModelAdmin):
    list_display = ("id", "card", "file_name", "file_size", "content_type", "uploaded_by", "created_at")
    search_fields = ("file_name", "uploaded_by__full_name")


@admin.register(ActivityLogModel)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ("id", "card", "user", "action_type", "details", "created_at")
    list_filter = ("action_type", "created_at")
    search_fields = ("details", "user__full_name")


@admin.register(NotificationModel)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "title", "is_read", "created_at")
    list_filter = ("is_read", "created_at")
    search_fields = ("title", "message", "user__email")


@admin.register(OfficeModel)
class OfficeAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "address", "latitude", "longitude", "radius_meters", "is_ip_check_enabled", "created_at")
    search_fields = ("name", "address", "ip_subnet")
    list_filter = ("is_ip_check_enabled",)


@admin.register(WorkScheduleModel)
class WorkScheduleAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "user", "department", "start_time", "end_time", "break_duration_minutes", "is_active")
    search_fields = ("name", "user__full_name", "department__name")
    list_filter = ("is_active", "department")


@admin.register(AttendanceRecordModel)
class AttendanceRecordAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "record_type", "timestamp", "is_within_radius", "verification_result", "is_edited", "edited_by")
    search_fields = ("user__full_name", "user__email", "edit_reason", "rejection_reason")
    list_filter = ("record_type", "verification_result", "is_within_radius", "is_edited")


@admin.register(AbsenceModel)
class AbsenceAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "category", "absence_type", "start_time", "end_time", "is_approved")
    search_fields = ("user__full_name", "reason", "comment")
    list_filter = ("category", "absence_type", "is_approved")


@admin.register(LocationLogModel)
class LocationLogAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "timestamp", "latitude", "longitude", "accuracy_meters", "source", "is_outside_office")
    search_fields = ("user__full_name",)
    list_filter = ("source", "is_outside_office")


@admin.register(ConsentModel)
class ConsentAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "consent_version", "is_granted", "granted_at", "revoked_at")
    search_fields = ("user__full_name", "user__email")
    list_filter = ("is_granted", "consent_version")


class FinancialReadOnlyAdmin(admin.ModelAdmin):
    """Financial documents are changed through guarded, audited APIs only."""
    def has_add_permission(self, request): return False
    def has_change_permission(self, request, obj=None): return False
    def has_delete_permission(self, request, obj=None): return False


class ExpenseAttachmentInline(admin.TabularInline):
    model = ExpenseAttachmentModel
    extra = 0
    readonly_fields = ("document_type", "file", "original_name", "created_at", "file_size", "uploaded_by")
    can_delete = False
    def has_add_permission(self, request, obj=None): return False
    def has_change_permission(self, request, obj=None): return False
    def has_delete_permission(self, request, obj=None): return False


@admin.register(ExpenseModel)
class ExpenseAdmin(FinancialReadOnlyAdmin):
    list_display = ("id", "purchase_date", "category", "amount", "currency", "payment_source", "status", "created_by", "department")
    list_filter = ("status", "payment_source", "currency", "department")
    search_fields = ("category", "supplier", "description", "created_by__full_name")
    inlines = [ExpenseAttachmentInline]


@admin.register(ReimbursementPaymentModel)
class ReimbursementPaymentAdmin(FinancialReadOnlyAdmin):
    list_display = ("id", "expense", "amount", "paid_at", "payment_method", "transaction_number", "created_by")


@admin.register(ExpenseActivityLogModel)
class ExpenseActivityLogAdmin(FinancialReadOnlyAdmin):
    list_display = ("id", "expense", "user", "action", "old_status", "new_status", "created_at")

