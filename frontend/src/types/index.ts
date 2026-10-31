export type RoleType = 'general_director' | 'manager' | 'employee' | 'accountant';

export type PriorityType = 'low' | 'medium' | 'high' | 'urgent';

export type LanguageCode = 'ru' | 'zh-Hans' | 'zh-Hant' | 'ky';

export interface User {
  id: number;
  email: string;
  full_name: string;
  role: RoleType;
  department_id: number | null;
  department_name?: string | null;
  phone?: string | null;
  interface_language: string;
  assigned_board_id: number | null;
  assigned_board_title?: string | null;
  is_active?: boolean;
  created_at?: string;
  permissions?: string[];
  system_permissions?: string[];
}

export type WorkspaceTab = 'board' | 'reports' | 'admin' | 'attendance' | 'finance' | 'hr' | 'approvals' | 'rbac' | 'procurement' | 'kpi' | 'warehouse';

export interface Employee {
  id: number; employee_no: string; email: string; full_name_ru: string; full_name_zh: string; full_name_ky: string;
  department_id: number | null; department_name?: string | null; position?: string; phone?: string;
  status: 'draft' | 'pending_approval' | 'active' | 'terminated' | 'rejected'; user_id?: number | null;
  created_at?: string; updated_at?: string;
}
export interface ApprovalRequest { id: number; business_type: string; business_id: number; status: string; applicant_id?: number; assigned_to_id?: number | null; current_node?: number; applicant_name?: string; created_at?: string; updated_at?: string; actions?: ApprovalAction[]; snapshot?: PaymentApprovalSnapshot; allowed_actions?: Array<'approve'|'reject'|'return'>; versions?: Array<{ version_no: number; reason: string; created_at: string }>; }
export interface ApprovalAction { id: number; action: string; comment?: string; actor_name?: string; created_at?: string; }
export interface SystemPermission { id: number; code: string; name: string; description?: string; }
export interface SystemRole { id: number; code: string; name: string; description?: string; active: boolean; permissions: SystemPermission[]; member_count?: number; }
export interface SystemRoleUser { id: number; full_name: string; email: string; system_role_ids?: number[]; }

export interface Department {
  id: number;
  name: string;
  created_at?: string;
}

export interface BoardMember {
  user_id: number;
  full_name: string;
  email: string;
  board_role: string;
  system_role: RoleType;
}

export interface BoardPermissions {
  can_manage_columns: boolean;
  can_manage_cards: boolean;
  can_move_cards: boolean;
  can_comment: boolean;
}

export interface ChecklistItem {
  id: number;
  card_id?: number;
  title: string;
  is_completed: boolean;
  order: number;
}

export interface Comment {
  id: number;
  user_id: number;
  user_full_name?: string;
  user_role?: string;
  text_ru: string;
  text_zh: string;
  text_ky: string;
  original_lang: string;
  created_at?: string;
}

export interface Attachment {
  id: number;
  file_path?: string;
  file_name: string;
  file_size: number;
  content_type: string;
  uploaded_by_id: number;
  uploader_name?: string;
  created_at?: string;
}

export interface ActivityLog {
  id: number;
  action_type: string;
  details: string;
  user_full_name?: string;
  created_at?: string;
}

export interface Card {
  id: number;
  column_id: number;
  title_ru: string;
  title_zh: string;
  title_ky: string;
  desc_ru: string;
  desc_zh: string;
  desc_ky: string;
  original_lang: string;
  priority: PriorityType;
  due_date: string | null;
  order: number;
  created_by_id?: number;
  created_at?: string;
  assignees: Array<{
    id: number;
    full_name: string;
    email: string;
    role: string;
  }>;
  checklists_summary?: {
    total: number;
    completed: number;
  };
  comments_count: number;
  attachments_count: number;
}

export interface Column {
  id: number;
  board_id: number;
  title_ru: string;
  title_zh: string;
  title_ky: string;
  original_lang: string;
  order: number;
  cards_count: number;
  cards: Card[];
}

export interface BoardDetail {
  id: number;
  title: string;
  department_id: number | null;
  department_name: string | null;
  background_theme: string;
  is_archived: boolean;
  created_at?: string;
  members: BoardMember[];
  columns: Column[];
  permissions: BoardPermissions;
}

export interface BoardSummary {
  id: number;
  title: string;
  department_id: number | null;
  department_name: string | null;
  background_theme: string;
  is_archived: boolean;
  columns_count: number;
  cards_count: number;
  members_count: number;
  created_at?: string;
}

export interface NotificationItem {
  id: number;
  title: string;
  message: string;
  entity_type: string;
  entity_id: number | null;
  is_read: boolean;
  created_at?: string;
}

export interface DepartmentReport {
  id: number;
  name: string;
  total: number;
  completed: number;
  overdue: number;
  in_progress: number;
  completion_rate: number;
}

export interface EmployeeReport {
  id: number;
  full_name: string;
  email: string;
  role: string;
  department_name: string;
  assigned_count: number;
  completed_count: number;
  overdue_count: number;
  in_progress_count: number;
  avg_completion_hours: number;
  completion_rate: number;
}

export interface AnalyticsData {
  period: string;
  start_date: string;
  end_date: string;
  summary: {
    total_tasks: number;
    completed_tasks: number;
    in_progress_tasks: number;
    overdue_tasks: number;
    bug_tasks: number;
    completion_rate: number;
  };
  departments: DepartmentReport[];
  employees: EmployeeReport[];
}

// Attendance & Time Tracking Types (Section 4.9)
export interface Office {
  id: number;
  name: string;
  address?: string;
  latitude: number;
  longitude: number;
  radius_meters: number;
  ip_subnet?: string;
  is_ip_check_enabled?: boolean;
}

export interface WorkSchedule {
  id: number;
  name: string;
  user_id?: number | null;
  user_full_name?: string | null;
  department_id?: number | null;
  department_name?: string | null;
  start_time: string;
  end_time: string;
  break_duration_minutes: number;
  timezone: string;
  is_active: boolean;
}

export interface AttendanceRecord {
  id: number;
  user_id: number;
  user_full_name: string;
  user_email: string;
  record_type: 'check_in' | 'check_out';
  timestamp: string;
  office_name: string;
  latitude?: number | null;
  longitude?: number | null;
  accuracy_meters?: number | null;
  is_within_radius: boolean;
  verification_result: 'verified' | 'rejected' | 'manual_override';
  rejection_reason?: string;
  is_edited: boolean;
  edited_by_name?: string | null;
  edit_reason?: string;
  original_timestamp?: string | null;
}

export interface ActiveBreak {
  id: number;
  absence_type: 'lunch' | 'business' | 'personal' | 'other';
  start_time: string;
  reason?: string;
  comment?: string;
}

export interface DayStatus {
  id: number;
  absence_type: 'vacation' | 'sick_leave' | 'business_trip' | 'day_off';
  start_time: string;
  end_time?: string | null;
  reason?: string;
}

export interface AttendanceStatus {
  is_checked_in: boolean;
  last_check_in_time?: string | null;
  last_check_out_time?: string | null;
  active_break?: ActiveBreak | null;
  day_status?: DayStatus | null;
  is_consent_granted: boolean;
  forgot_checkout_reminder?: boolean;
  office?: Office | null;
  schedule?: WorkSchedule | null;
}

export interface TimesheetDailyRecord {
  day: number;
  date: string;
  is_weekend: boolean;
  check_in?: string | null;
  check_out?: string | null;
  worked_hours: number;
  late_minutes: number;
  early_minutes: number;
  day_status?: string | null;
}

export interface TimesheetEmployee {
  user_id: number;
  full_name: string;
  email: string;
  department_name: string;
  role: string;
  days_worked: number;
  total_worked_hours: number;
  late_count: number;
  total_late_minutes: number;
  early_count: number;
  total_early_minutes: number;
  lunch_hours: number;
  business_hours: number;
  personal_hours: number;
  other_hours: number;
  vacation_days: number;
  sick_days: number;
  trip_days: number;
  day_off_days: number;
  daily_records: TimesheetDailyRecord[];
}

export interface TimesheetDepartment {
  department_name: string;
  employees_count: number;
  total_worked_hours: number;
  total_late_count: number;
  total_late_minutes: number;
  total_early_count: number;
}

export interface TimesheetReport {
  year: number;
  month: number;
  month_name: string;
  num_days: number;
  total_employees: number;
  employees: TimesheetEmployee[];
  departments: TimesheetDepartment[];
}



export type KpiCycle = 'month' | 'quarter' | 'year';
export type KpiAction = 'self_score' | 'manager_score' | 'review' | 'acknowledge' | 'archive';
export type KpiStatus = 'self_review' | 'manager_review' | 'senior_review' | 'confirmed';
export interface KpiTemplateItem { id?: number; name_ru: string; name_zh: string; name_ky: string; weight: string; formula: string; }
export interface KpiTemplate { is_active: boolean; id: number; name: string; position_code: string; cycle: KpiCycle; items: KpiTemplateItem[]; }
export interface KpiAssignee { id: number; full_name_ru: string; full_name_zh: string; full_name_ky: string; position: string; department_id: number | null; }
export interface KpiComments { ru: string; zh: string; ky: string; }
export interface KpiHistory { id: number; action: string; actor_name: string; created_at: string; old_data: Record<string, unknown>; new_data: Record<string, unknown>; }
export interface KpiTask {
  id: number; employee_id: number; template_id: number; year: number; period: string; status: KpiStatus;
  employee_name_ru: string; employee_name_zh: string; employee_name_ky: string; template_name: string; position_code: string; cycle: KpiCycle;
  self_score: string | null; manager_score: string | null; final_score: string | null;
  acknowledged_at: string | null; archived_at: string | null; reviewed_at: string | null;
  manager_scored_by_id: number | null; reviewed_by_id: number | null; allowed_actions: KpiAction[];
  comments: { self: KpiComments; manager: KpiComments; review: KpiComments }; history: KpiHistory[];
}

// Online warehouse API: all selectors and action flags are scoped by the server.
export interface WarehouseNames { name_ru: string; name_ky: string; name_zh: string; }
export interface WarehouseRecordNames { warehouse_name_ru: string; warehouse_name_ky: string; warehouse_name_zh: string; }
export interface WarehouseCatalog {
  warehouses: Array<WarehouseNames & { id: number; locations: Array<{ id: number; code: string }> }>;
  skus: Array<WarehouseNames & { id: number; sku_code: string }>;
  purchase_orders: Array<{ id: number; po_no: string; currency: string; items: Array<WarehouseNames & { id: number; sku_id: number; sku_code: string; ordered_qty: number; received_qty: number; unit_cost?: string }> }>;
  permissions: string[];
}
export interface WarehouseInventory extends WarehouseNames, WarehouseRecordNames { id: number; warehouse_id: number; location_id: number | null; location_code: string | null; sku_id: number; sku_code: string; qty: string; avg_cost?: string; batches: Array<{ batch_no: string; expiry_date: string; qty: string }> }
export interface WarehouseMovement extends WarehouseNames, WarehouseRecordNames { id: number; warehouse_id: number; location_id: number | null; location_code: string | null; sku_id: number; sku_code: string; qty_delta: string; unit_cost?: string; movement_type: string; source_type: string; source_id: number; source_no?: string | null; reason: string; posted_at: string }
export interface WarehouseReceiptLine extends WarehouseNames { id: number; po_item_id: number; sku_id: number; sku_code: string; qty: number; location_id: number | null; location_code: string | null; batch_no: string; expiry_date: string | null; discrepancy_reason: string; unit_cost?: string }
export interface WarehouseReceipt extends WarehouseRecordNames { id: number; receipt_no: string; purchase_order_id: number; po_no: string; warehouse_id: number; status: string; comment: string; received_at: string; allowed_actions: string[]; items: WarehouseReceiptLine[] }
export interface WarehouseCount extends WarehouseRecordNames { id: number; count_no: string; warehouse_id: number; status: string; created_at: string; allowed_actions: string[]; items: Array<WarehouseNames & { sku_id: number; sku_code: string; system_qty: string; actual_qty: string; reason: string }> }
export interface WarehouseExpiry { as_of: string; days: number; batches_count?: number; certificates_count?: number; truncated?: boolean; batches: Array<WarehouseNames & Partial<WarehouseRecordNames> & { id: number; warehouse_id: number; location_id?: number | null; location_code?: string | null; sku_id: number; sku_code: string; batch_no: string; expiry_date: string; qty: string; expired: boolean }>; certificates: Array<{ id: number; sku_id: number; sku_code: string; number: string; expires_at: string; expired: boolean }> }
export interface WarehouseListQuery { warehouse_id?: number; offset?: number; limit?: number; id?: number }
export interface WarehouseReceiptInput { receipt_no: string; purchase_order_id: number; warehouse_id: number; comment: string; items: Array<{ po_item_id: number; qty: number; location_id?: number; batch_no?: string; expiry_date?: string; discrepancy_reason: string }> }
export interface WarehouseCountInput { count_no: string; warehouse_id: number; items: Array<{ sku_id: number; actual_qty: string; reason: string }> }

export type TransferStatus = 'draft' | 'pending_approval' | 'approved' | 'in_transit' | 'received' | 'rejected' | 'cancelled';
export type TransferAction = 'edit' | 'submit' | 'review' | 'dispatch' | 'receive' | 'cancel';
export interface TransferWarehouse extends WarehouseNames { id: number; locations: Array<{ id: number; code: string }> }
export interface TransferCatalog {
  sources: TransferWarehouse[]; destinations: TransferWarehouse[];
  skus: Array<WarehouseNames & { id: number; sku_code: string }>;
  stock: Array<{ sku_id: number; warehouse_id: number; location_id: number | null; location_code: string | null; qty: string; unbatched_qty: string; batches: Array<{ batch_no: string; expiry_date: string; qty: string }> }>;
  permissions: string[];
}
export interface TransferLine extends WarehouseNames {
  id: number; sku_id: number; sku_code: string; qty: number; source_location_id: number | null; source_location_code: string | null;
  destination_location_id: number | null; destination_location_code: string | null; batch_no: string; expiry_date: string | null;
  in_transit_qty: string; unit_cost?: string;
}
export interface StockTransfer {
  id: number; transfer_no: string; source_warehouse_id: number; destination_warehouse_id: number;
  source_name_ru: string; source_name_ky: string; source_name_zh: string;
  destination_name_ru: string; destination_name_ky: string; destination_name_zh: string;
  status: TransferStatus; created_at: string; approved_at: string | null; dispatched_at: string | null; received_at: string | null;
  created_by_name: string; approved_by_name: string | null; dispatched_by_name: string | null; received_by_name: string | null;
  comment: string; review_comment: string; in_transit_qty: string; allowed_actions: TransferAction[]; items: TransferLine[];
  history: Array<{ id: number; action: string; actor_name: string; created_at: string; comment: string }>;
}
export interface TransferInput {
  transfer_no: string; source_warehouse_id: number; destination_warehouse_id: number; comment: string;
  items: Array<{ sku_id: number; qty: number; source_location_id?: number; destination_location_id?: number; batch_no?: string; expiry_date?: string }>;
}
export interface TransferQuery extends WarehouseListQuery { status?: TransferStatus }

export type WriteoffStatus = 'draft' | 'pending_approval' | 'approved' | 'posted' | 'rejected' | 'cancelled';
export type WriteoffAction = 'edit' | 'upload_photo' | 'delete_photo' | 'submit' | 'review' | 'post' | 'cancel';
export interface WriteoffCatalog {
  warehouses: TransferWarehouse[];
  skus: Array<WarehouseNames & { id: number; sku_code: string }>;
  stock: TransferCatalog['stock'];
  permissions: string[];
}
export interface WriteoffLine extends WarehouseNames {
  id: number; sku_id: number; sku_code: string; qty: string; location_id: number | null; location_code: string | null;
  batch_no: string; expiry_date: string | null; unit_cost?: string;
}
export interface WriteoffPhoto { id: number; file_name: string; content_type: string; size: number; download_url: string }
export interface StockWriteoff extends WarehouseRecordNames {
  id: number; writeoff_no: string; warehouse_id: number; status: WriteoffStatus; reason: string; review_comment: string;
  created_at: string; created_by_name: string; approved_at: string | null; approved_by_name: string | null;
  posted_at: string | null; posted_by_name: string | null; allowed_actions: WriteoffAction[];
  items: WriteoffLine[]; photos: WriteoffPhoto[];
  history: Array<{ id: number; action: string; actor_name: string; created_at: string; comment: string }>;
}
export interface WriteoffInput {
  writeoff_no: string; warehouse_id: number; reason: string;
  items: Array<{ sku_id: number; qty: string; location_id?: number; batch_no?: string; expiry_date?: string }>;
}
export interface WriteoffQuery extends WarehouseListQuery { status?: WriteoffStatus }


export type SupplierReturnStatus = WriteoffStatus;
export type SupplierReturnReason = 'damage' | 'expiry' | 'other';
export interface SupplierReturnReceiptLine extends WarehouseNames {
  receipt_item_id: number; sku_id: number; sku_code: string; location_id: number | null; location_code: string | null;
  batch_no: string; expiry_date: string | null; received_qty: number; returned_qty: number; returnable_qty: number;
}
export interface SupplierReturnReceipt {
  id: number; receipt_no: string; warehouse_id: number; supplier_id: number; supplier_name: string; items: SupplierReturnReceiptLine[];
}
export interface SupplierReturnCatalog { warehouses: Array<WarehouseNames & {id:number}>; receipts: SupplierReturnReceipt[]; permissions: string[]; receipt_count: number; limit: number; offset: number }
export interface SupplierReturn extends WarehouseRecordNames {
  id: number; return_no: string; receipt_id: number; receipt_no: string; warehouse_id: number; supplier_id: number; supplier_name: string;
  reason_type: SupplierReturnReason; reason: string; status: SupplierReturnStatus; review_comment: string;
  created_at: string; created_by_name: string; approved_at: string | null; approved_by_name: string | null;
  posted_at: string | null; posted_by_name: string | null; allowed_actions: WriteoffAction[]; finance_review_status: string | null; photos_required: boolean;
  items: Array<WriteoffLine & { receipt_item_id: number }>; photos: WriteoffPhoto[]; history: StockWriteoff['history'];
}
export interface SupplierReturnInput { return_no: string; receipt_id: number; reason_type: SupplierReturnReason; reason: string; items: Array<{receipt_item_id: number; qty: number}> }
export interface SupplierReturnFinance {
  id: number; return_id: number; return_no: string; receipt_id: number; receipt_no: string; supplier_id: number; supplier_name: string;
  warehouse_id: number; status: 'pending'; created_at: string; posted_at: string; source_currency: string; valuation_currency: null; valuation_status: 'currency_unresolved'; stock_valuation: string; photos: WriteoffPhoto[];
  items: Array<WarehouseNames & { receipt_item_id: number; sku_id: number; sku_code: string; qty: string; unit_cost: string }>;
}

export interface SupplierReturnCorrection {
  id: number; review_id: number; return_id: number; payable_id: number; request_id: string;
  amount: string; currency: string; posting_date: string; document_no: string; reason: string;
  outstanding_before: string; outstanding_after: string; confirmed_by_name: string; confirmed_at: string;
}
export interface SupplierReturnCorrectionInput {
  request_id: string; payable_id: number; amount: string; currency: string;
  posting_date: string; document_no: string; reason: string;
}
export interface SupplierReturnCorrectionPayable {
  id: number; supplier_id: number; purchase_order_id: number; source_type: string; source_id: number;
  amount: string; outstanding_amount: string; currency: string; status: 'open' | 'partially_paid';
}
export interface SupplierReturnCorrectionsResponse {
  review_id: number; review_status: 'pending'; corrections: SupplierReturnCorrection[]; correction_count: number;
  payables: SupplierReturnCorrectionPayable[]; payable_count: number; can_confirm: boolean;
  limit: number; offset: number; payable_limit: number; payable_offset: number;
}


export interface FinancePeriod {
  year: number; month: number; is_closed: boolean;
  closed_by_name: string | null; closed_at: string | null; close_reason: string;
}
export interface FinancePeriodsResponse { year: number; items: FinancePeriod[]; can_close: boolean }


export type PaymentRequestStatus = 'draft'|'pending_approval'|'approved'|'returned'|'rejected'|'cancelled'|'paid';
export interface PaymentProof { id:number; file_name:string; content_type:string; size:number; download_url:string }
export interface PaymentApprovalSnapshot { payment_request_id:number; request_no:string; payable_id:number; supplier_id:number; supplier_name:string; account_id:number; account_name:string; amount:string; currency:string; planned_payment_date:string; purpose:string; route:Array<{order:number;assignee_id:number;assignee_name:string}>; proofs:PaymentProof[] }
export interface PaymentRequestInput { request_id:string; request_no:string; payable_id:number; account_id:number; amount:string; currency:string; planned_payment_date:string; purpose:string }
export interface FinancePaymentRequest { id:number; request_id:string; request_no:string; payable_id:number; supplier_id:number; supplier_name:string; payable_outstanding_amount:string; account_id:number; account_name:string; amount:string; currency:string; planned_payment_date:string; purpose:string; status:PaymentRequestStatus; created_by_id:number; created_by_name:string; created_at:string; approval_id:number|null; approval_status:string|null; assigned_to_id:number|null; assigned_to_name:string|null; current_node:number|null; payment_id:number|null; allowed_actions:string[]; proofs:PaymentProof[]; history:Array<{action:string;actor_id:number;actor_name:string;comment:string;created_at:string}> }
export interface PaymentRequestCatalog { payables:Array<{id:number;supplier_id:number;supplier_name:string;source_id:number;amount:string;outstanding_amount:string;currency:string;status:string}>; payable_count:number; accounts:Array<{id:number;name:string;currency:string}>; limit:number; offset:number; flow_configured:boolean }
export interface PaymentExecutionInput { payment_request_id:number; account_id:number; amount:string; payment_date:string; transaction_no:string; proof_id:number }
export interface PaymentExecutionResult { id:number; payment_request_id:number; payable:{id:number;amount:string;outstanding_amount:string;currency:string;status:string} }
