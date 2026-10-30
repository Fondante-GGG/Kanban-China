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
from backend.presentation.api.attendance_views import (
    attendance_status_view, check_in_view, check_out_view, leave_absence_view,
    resume_absence_view, location_log_view, attendance_records_view,
    attendance_record_detail_view, consent_view, day_status_view,
    offices_view, office_detail_view, work_schedules_view,
    attendance_timesheet_view, attendance_export_view
)
from backend.presentation.api.expense_views import (
    expenses_view, expense_detail_view, expense_status_view, expense_attachments_view,
    expense_attachment_download_view, reimbursement_payment_view, expense_analytics_view, expense_export_view
)

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

    # Attendance & Geolocation (Section 4.9)
    path("attendance/status", attendance_status_view, name="api-attendance-status"),
    path("attendance/check-in", check_in_view, name="api-attendance-check-in"),
    path("attendance/check-out", check_out_view, name="api-attendance-check-out"),
    path("attendance/leave", leave_absence_view, name="api-attendance-leave"),
    path("attendance/resume", resume_absence_view, name="api-attendance-resume"),
    path("attendance/location-log", location_log_view, name="api-attendance-location-log"),
    path("attendance/records", attendance_records_view, name="api-attendance-records"),
    path("attendance/records/<int:record_id>", attendance_record_detail_view, name="api-attendance-record-detail"),
    path("attendance/consent", consent_view, name="api-attendance-consent"),
    path("attendance/day-status", day_status_view, name="api-attendance-day-status"),
    path("attendance/offices", offices_view, name="api-attendance-offices"),
    path("attendance/offices/<int:office_id>", office_detail_view, name="api-attendance-office-detail"),
    path("attendance/schedules", work_schedules_view, name="api-attendance-schedules"),
    path("attendance/reports/timesheet", attendance_timesheet_view, name="api-attendance-timesheet"),
    path("attendance/reports/export", attendance_export_view, name="api-attendance-export"),

    # Finance: expenses, receipts and employee reimbursements
    path("expenses", expenses_view, name="api-expenses"),
    path("expenses/analytics", expense_analytics_view, name="api-expense-analytics"),
    path("expenses/export", expense_export_view, name="api-expense-export"),
    path("expenses/<int:expense_id>", expense_detail_view, name="api-expense-detail"),
    path("expenses/<int:expense_id>/status", expense_status_view, name="api-expense-status"),
    path("expenses/<int:expense_id>/attachments", expense_attachments_view, name="api-expense-attachments"),
    path("expenses/<int:expense_id>/payment", reimbursement_payment_view, name="api-expense-payment"),
    path("expense-attachments/<int:attachment_id>/download", expense_attachment_download_view, name="api-expense-attachment-download"),
]
