from django.contrib import admin
from backend.infrastructure.persistence.models import (
    DepartmentModel, UserModel, BoardModel, BoardMemberModel, ColumnModel,
    CardModel, CardAssigneeModel, ChecklistModel, CommentModel, AttachmentModel,
    ActivityLogModel, NotificationModel
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
