from django.urls import path
from backend.presentation.api.auth_views import login_view, me_view, reset_password_view
from backend.presentation.api.user_views import (
    users_list_create_view, user_detail_view, departments_view, department_detail_view
)
from backend.presentation.api.board_views import boards_list_create_view, board_detail_view
from backend.presentation.api.column_views import columns_create_view, column_detail_view, reorder_columns_view
from backend.presentation.api.card_views import cards_create_view, card_detail_view, card_move_view
from backend.presentation.api.checklist_views import checklists_create_view, checklist_toggle_view
from backend.presentation.api.comment_views import comments_create_view, comment_detail_view
from backend.presentation.api.attachment_views import attachments_upload_view, attachment_detail_view
from backend.presentation.api.notification_views import notifications_list_view
from backend.presentation.api.report_views import analytics_report_view, export_report_view
from backend.presentation.api.translate_views import convert_chinese_view, translate_text_view

urlpatterns = [
    # Auth
    path("auth/login", login_view, name="api-login"),
    path("auth/me", me_view, name="api-me"),
    path("auth/reset-password", reset_password_view, name="api-reset-password"),

    # Users & Departments (Admin)
    path("users", users_list_create_view, name="api-users"),
    path("users/<int:user_id>", user_detail_view, name="api-user-detail"),
    path("departments", departments_view, name="api-departments"),
    path("departments/<int:dept_id>", department_detail_view, name="api-department-detail"),

    # Boards
    path("boards", boards_list_create_view, name="api-boards"),
    path("boards/<int:board_id>", board_detail_view, name="api-board-detail"),

    # Columns
    path("columns", columns_create_view, name="api-columns"),
    path("columns/<int:column_id>", column_detail_view, name="api-column-detail"),
    path("columns/reorder", reorder_columns_view, name="api-columns-reorder"),

    # Cards
    path("cards", cards_create_view, name="api-cards"),
    path("cards/<int:card_id>", card_detail_view, name="api-card-detail"),
    path("cards/<int:card_id>/move", card_move_view, name="api-card-move"),

    # Checklists
    path("checklists", checklists_create_view, name="api-checklists"),
    path("checklists/<int:item_id>/toggle", checklist_toggle_view, name="api-checklist-toggle"),
    path("checklists/<int:item_id>", checklist_toggle_view, name="api-checklist-delete"),

    # Comments
    path("comments", comments_create_view, name="api-comments"),
    path("comments/<int:comment_id>", comment_detail_view, name="api-comment-delete"),

    # Attachments
    path("attachments", attachments_upload_view, name="api-attachments"),
    path("attachments/<int:attachment_id>", attachment_detail_view, name="api-attachment-delete"),

    # Notifications
    path("notifications", notifications_list_view, name="api-notifications"),

    # Reports
    path("reports/analytics", analytics_report_view, name="api-reports-analytics"),
    path("reports/export", export_report_view, name="api-reports-export"),

    # Translation
    path("translate/convert-chinese", convert_chinese_view, name="api-convert-chinese"),
    path("translate/text", translate_text_view, name="api-translate-text"),
]
