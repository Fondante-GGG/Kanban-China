from backend.presentation.api.finance_period_views import finance_periods_view, close_finance_period_view
from backend.presentation.api.finance_return_views import supplier_return_corrections_view
from backend.presentation.api.warehouse_return_views import return_catalog_view, returns_view, return_detail_view, return_photos_view, return_photo_detail_view, return_photo_download_view, return_action_view, finance_supplier_returns_view, finance_supplier_return_photo_view
from backend.presentation.api.warehouse_writeoff_views import writeoff_catalog_view, writeoffs_view, writeoff_detail_view, writeoff_photos_view, writeoff_photo_detail_view, writeoff_photo_download_view, writeoff_action_view
from backend.presentation.api.warehouse_transfer_views import transfer_catalog_view, transfer_detail_view, transfer_action_view
from django.urls import path
from backend.presentation.api.auth_views import login_view, me_view, reset_password_view, profile_language_view
from backend.presentation.api.platform_views import employee_documents_view
from backend.presentation.api.user_views import (
    users_list_create_view, user_detail_view, departments_view, department_detail_view
)
from backend.presentation.api.board_views import boards_list_create_view, board_detail_view
from backend.presentation.api.column_views import columns_create_view, column_detail_view, reorder_columns_view
from backend.presentation.api.card_views import cards_create_view, card_detail_view, card_move_view
from backend.presentation.api.checklist_views import checklists_create_view, checklist_toggle_view
from backend.presentation.api.comment_views import comments_create_view, comment_detail_view
from backend.presentation.api.attachment_views import attachments_upload_view, attachment_detail_view, attachment_download_view
from backend.presentation.api.notification_views import notifications_list_view
from backend.presentation.api.report_views import analytics_report_view, export_report_view
from backend.presentation.api.translate_views import convert_chinese_view, translate_text_view
from backend.presentation.api.attendance_views import (
    attendance_status_view, check_in_view, check_out_view, leave_absence_view,
    resume_absence_view, location_log_view, attendance_records_view,
    attendance_record_detail_view, consent_view, day_status_view,
    offices_view, office_detail_view, work_schedules_view,
    attendance_timesheet_view, attendance_export_view
    , confirm_monthly_timesheet_view
)
from backend.presentation.api.expense_views import (
    expenses_view, expense_detail_view, expense_status_view, expense_attachments_view,
    expense_attachment_download_view, reimbursement_payment_view, expense_analytics_view, expense_export_view
)
from backend.presentation.api.warehouse_views import warehouse_catalog_view, warehouse_movements_view
from backend.presentation.api.procurement_views import suppliers_view, supplier_submit_view, skus_view, sku_submit_view, sku_certificates_view, supplier_quotes_view, purchase_orders_view, purchase_order_submit_view, purchase_receipts_view, stock_transfers_view, stock_counts_view, post_purchase_receipt_view, warehouse_inventory_view, expiry_alerts_view, approve_stock_count_view, post_stock_transfer_view
from backend.presentation.api.finance_payment_request_views import (payment_requests_view,payment_request_catalog_view,payment_request_detail_view,payment_request_action_view,payment_request_proofs_view,payment_request_proof_delete_view,payment_request_proof_download_view)
from backend.presentation.api.finance_platform_views import finance_accounts_view, finance_payables_view, supplier_statements_view, finance_payment_view, confirm_supplier_statement_view
from backend.presentation.api.kpi_views import kpi_templates_view, kpi_tasks_view, kpi_task_score_view, kpi_task_acknowledge_view, kpi_task_review_view, kpi_task_archive_view, kpi_assignees_view
from backend.presentation.api.admin_platform_views import assets_view, asset_custody_view, supply_requests_view, meeting_bookings_view, notices_view, licenses_view
from backend.presentation.api.salary_views import salaries_view
from backend.presentation.api.platform_views import (
    employees_view, employee_detail_view, employee_submit_view, approval_action_view,
    rbac_roles_view, rbac_permissions_view, rbac_users_view, rbac_role_permissions_view, user_system_roles_view,
    onboarding_link_view, onboarding_confirm_view, approvals_inbox_view, approval_detail_view, approval_flows_view, audit_view,
)

urlpatterns = [
    # Platform foundation: independent module RBAC, HR lifecycle and approvals
    path("hr/employees", employees_view, name="api-hr-employees"),
    path("hr/employees/<int:employee_id>", employee_detail_view, name="api-hr-employee"),
    path("hr/employees/<int:employee_id>/submit", employee_submit_view, name="api-hr-employee-submit"),
    path("hr/employees/<int:employee_id>/termination/submit", lambda request, employee_id: employee_submit_view(request, employee_id, termination=True), name="api-hr-employee-termination-submit"),
    path("approvals/<int:approval_id>/actions", approval_action_view, name="api-approval-action"),
    path("approvals/inbox", approvals_inbox_view, name="api-approvals-inbox"),
    path("approval-flows", approval_flows_view, name="api-approval-flows"),
    path("approvals/<int:approval_id>", approval_detail_view, name="api-approval-detail"),
    path("audit", audit_view, name="api-audit"),
    path("rbac/roles", rbac_roles_view, name="api-rbac-roles"),
    path("rbac/permissions", rbac_permissions_view, name="api-rbac-permissions"),
    path("rbac/users", rbac_users_view, name="api-rbac-users"),
    path("rbac/roles/<int:role_id>/permissions", rbac_role_permissions_view, name="api-rbac-role-permissions"),
    path("users/<int:user_id>/system-roles", user_system_roles_view, name="api-user-system-roles"),
    path("hr/employees/<int:employee_id>/onboarding-link", onboarding_link_view, name="api-hr-onboarding-link"),
    path("auth/onboarding/confirm", onboarding_confirm_view, name="api-onboarding-confirm"),
    # Auth
    path("auth/login", login_view, name="api-login"),
    path("auth/me", me_view, name="api-me"),
    path("profile/language", profile_language_view, name="api-profile-language"),
    path("auth/reset-password", reset_password_view, name="api-reset-password"),
    path("hr/employees/<int:employee_id>/documents", employee_documents_view, name="api-employee-documents"),

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
    path("attachments/<int:attachment_id>/download", attachment_download_view, name="api-attachment-download"),

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
    path("attendance/timesheets/confirm", confirm_monthly_timesheet_view, name="api-attendance-timesheet-confirm"),
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
    path("procurement/suppliers", suppliers_view, name="api-suppliers"),
    path("procurement/suppliers/<int:supplier_id>/submit", supplier_submit_view, name="api-supplier-submit"),
    path("procurement/skus/<int:sku_id>/submit", sku_submit_view, name="api-sku-submit"),
    path("procurement/skus/<int:sku_id>/certificates", sku_certificates_view, name="api-sku-certificates"),
    path("procurement/skus", skus_view, name="api-skus"),
    path("procurement/quotes", supplier_quotes_view, name="api-supplier-quotes"),
    path("procurement/purchase-orders", purchase_orders_view, name="api-purchase-orders"),
    path("procurement/purchase-orders/<int:order_id>/submit", purchase_order_submit_view, name="api-purchase-order-submit"),
    path("warehouse/catalog", warehouse_catalog_view, name="api-warehouse-catalog"),
    path("warehouse/movements", warehouse_movements_view, name="api-warehouse-movements"),
    path("warehouse/receipts", purchase_receipts_view, name="api-purchase-receipts"),
    path("warehouse/receipts/<int:receipt_id>/post", post_purchase_receipt_view, name="api-post-purchase-receipt"),
    path("warehouse/inventory", warehouse_inventory_view, name="api-warehouse-inventory"),
    path("warehouse/alerts/expiry", expiry_alerts_view, name="api-warehouse-expiry-alerts"),
    path("warehouse/counts", stock_counts_view, name="api-warehouse-counts"),
    path("warehouse/counts/<int:count_id>/approve", approve_stock_count_view, name="api-warehouse-count-approve"),
    path("warehouse/returns/catalog", return_catalog_view, name="api-return-catalog"),
    path("warehouse/returns", returns_view, name="api-returns"),
    path("warehouse/returns/<int:return_id>", return_detail_view, name="api-return-detail"),
    path("warehouse/returns/<int:return_id>/photos", return_photos_view, name="api-return-photos"),
    path("warehouse/returns/<int:return_id>/photos/<int:photo_id>", return_photo_detail_view, name="api-return-photo-detail"),
    path("warehouse/returns/<int:return_id>/photos/<int:photo_id>/download", return_photo_download_view, name="api-return-photo-download"),
    path("warehouse/returns/<int:return_id>/<str:action>", return_action_view, name="api-return-action"),
    path("finance/supplier-returns/<int:review_id>/photos/<int:photo_id>/download", finance_supplier_return_photo_view, name="api-finance-return-photo"),
    path("finance/supplier-returns/<int:review_id>/corrections", supplier_return_corrections_view, name="api-finance-return-corrections"),
    path("finance/supplier-returns", finance_supplier_returns_view, name="api-finance-supplier-returns"),
    path("warehouse/writeoffs/catalog", writeoff_catalog_view, name="api-writeoff-catalog"),
    path("warehouse/writeoffs", writeoffs_view, name="api-writeoffs"),
    path("warehouse/writeoffs/<int:writeoff_id>", writeoff_detail_view, name="api-writeoff-detail"),
    path("warehouse/writeoffs/<int:writeoff_id>/photos", writeoff_photos_view, name="api-writeoff-photos"),
    path("warehouse/writeoffs/<int:writeoff_id>/photos/<int:photo_id>", writeoff_photo_detail_view, name="api-writeoff-photo-detail"),
    path("warehouse/writeoffs/<int:writeoff_id>/photos/<int:photo_id>/download", writeoff_photo_download_view, name="api-writeoff-photo-download"),
    path("warehouse/writeoffs/<int:writeoff_id>/<str:action>", writeoff_action_view, name="api-writeoff-action"),
    path("warehouse/transfers/catalog", transfer_catalog_view, name="api-transfer-catalog"),
    path("warehouse/transfers/<int:transfer_id>", transfer_detail_view, name="api-transfer-detail"),
    path("warehouse/transfers", stock_transfers_view, name="api-warehouse-transfers"),
    path("warehouse/transfers/<int:transfer_id>/post", post_stock_transfer_view, name="api-warehouse-transfer-post"),
    path("warehouse/transfers/<int:transfer_id>/<str:action>", transfer_action_view, name="api-transfer-action"),
    path("finance/periods", finance_periods_view, name="api-finance-periods"),
    path("finance/periods/<int:year>/<int:month>/close", close_finance_period_view, name="api-finance-period-close"),
    path("finance/accounts", finance_accounts_view, name="api-finance-accounts"),
    path("finance/payment-requests",payment_requests_view),
    path("finance/payment-requests/catalog",payment_request_catalog_view),
    path("finance/payment-requests/<int:request_id>",payment_request_detail_view),
    path("finance/payment-requests/<int:request_id>/proofs",payment_request_proofs_view),
    path("finance/payment-requests/<int:request_id>/proofs/<int:proof_id>",payment_request_proof_delete_view),
    path("finance/payment-requests/<int:request_id>/proofs/<int:proof_id>/download",payment_request_proof_download_view),
    path("finance/payment-requests/<int:request_id>/<str:action>",payment_request_action_view),
    path("finance/payables", finance_payables_view, name="api-finance-payables"),
    path("finance/supplier-statements", supplier_statements_view, name="api-supplier-statements"),
    path("finance/payables/<int:payable_id>/payments", finance_payment_view, name="api-finance-payment"),
    path("finance/supplier-statements/<int:statement_id>/confirm", confirm_supplier_statement_view, name="api-confirm-supplier-statement"),
    path("kpi/templates", kpi_templates_view, name="api-kpi-templates"),
    path("kpi/assignees", kpi_assignees_view, name="api-kpi-assignees"),
    path("kpi/tasks", kpi_tasks_view, name="api-kpi-tasks"),
    path("kpi/tasks/<int:task_id>/score", kpi_task_score_view, name="api-kpi-score"),
    path("kpi/tasks/<int:task_id>/acknowledge", kpi_task_acknowledge_view, name="api-kpi-acknowledge"),
    path("kpi/tasks/<int:task_id>/review", kpi_task_review_view, name="api-kpi-review"),
    path("kpi/tasks/<int:task_id>/archive", kpi_task_archive_view, name="api-kpi-archive"),
    path("admin/assets", assets_view, name="api-admin-assets"),
    path("admin/assets/<int:asset_id>/custody", asset_custody_view, name="api-admin-asset-custody"),
    path("admin/supply-requests", supply_requests_view, name="api-admin-supply-requests"),
    path("admin/meeting-bookings", meeting_bookings_view, name="api-admin-meeting-bookings"),
    path("admin/notices", notices_view, name="api-admin-notices"),
    path("admin/licenses", licenses_view, name="api-admin-licenses"),
    path("finance/salaries", salaries_view, name="api-finance-salaries"),
]
