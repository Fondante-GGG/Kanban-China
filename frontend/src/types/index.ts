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
