export type RoleType = 'general_director' | 'manager' | 'employee';

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
}

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
  file_path: string;
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

