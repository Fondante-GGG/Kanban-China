const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8080/api';

class ApiClient {
  private token: string | null = null;

  constructor() {
    if (typeof window !== 'undefined') {
      this.token = localStorage.getItem('kanban_token');
    }
  }

  setToken(token: string | null) {
    this.token = token;
    if (typeof window !== 'undefined') {
      if (token) {
        localStorage.setItem('kanban_token', token);
      } else {
        localStorage.removeItem('kanban_token');
      }
    }
  }

  getToken(): string | null {
    if (!this.token && typeof window !== 'undefined') {
      this.token = localStorage.getItem('kanban_token');
    }
    return this.token;
  }

  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const headers: Record<string, string> = {
      ...(options.headers as Record<string, string>),
    };

    const token = this.getToken();
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    if (!(options.body instanceof FormData)) {
      headers['Content-Type'] = 'application/json';
    }

    const res = await fetch(`${API_BASE_URL}${endpoint}`, {
      ...options,
      headers,
    });

    if (res.status === 401) {
      this.setToken(null);
      if (typeof window !== 'undefined' && !window.location.pathname.includes('/login')) {
        // can notify or redirect
      }
    }

    const contentType = res.headers.get('content-type') || '';
    if (contentType.includes('application/json')) {
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.error || 'Server error occurred');
      }
      return data;
    }

    if (!res.ok) {
      throw new Error(`HTTP error ${res.status}`);
    }

    return res as unknown as T;
  }

  // Auth
  async login(email: string, password: string) {
    const res = await this.request<{ access_token: string; user: any }>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });
    this.setToken(res.access_token);
    return res;
  }

  async getMe() {
    return this.request<any>('/auth/me');
  }

  async resetPassword(newPassword: string, userId?: number) {
    return this.request<{ message: string }>('/auth/reset-password', {
      method: 'POST',
      body: JSON.stringify({ new_password: newPassword, user_id: userId }),
    });
  }

  // Boards
  async getBoards() {
    return this.request<{ boards: any[] }>('/boards');
  }

  async getBoardDetail(boardId: number, params?: { search?: string; priority?: string; assignee_id?: number }) {
    const query = new URLSearchParams();
    if (params?.search) query.append('search', params.search);
    if (params?.priority) query.append('priority', params.priority);
    if (params?.assignee_id) query.append('assignee_id', params.assignee_id.toString());
    const qStr = query.toString() ? `?${query.toString()}` : '';
    return this.request<any>(`/boards/${boardId}${qStr}`);
  }

  async createBoard(data: { title: string; department_id?: number; background_theme?: string; manager_id?: number; employee_ids?: number[] }) {
    return this.request<any>('/boards', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async updateBoard(boardId: number, data: any) {
    return this.request<any>(`/boards/${boardId}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  async deleteBoard(boardId: number) {
    return this.request<any>(`/boards/${boardId}`, {
      method: 'DELETE',
    });
  }

  // Columns
  async createColumn(data: { board_id: number; title: string; language: string; order?: number }) {
    return this.request<any>('/columns', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async updateColumn(columnId: number, data: { title?: string; language?: string; order?: number }) {
    return this.request<any>(`/columns/${columnId}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  async deleteColumn(columnId: number) {
    return this.request<any>(`/columns/${columnId}`, {
      method: 'DELETE',
    });
  }

  async reorderColumns(boardId: number, columnOrders: Array<{ id: number; order: number }>) {
    return this.request<any>('/columns/reorder', {
      method: 'POST',
      body: JSON.stringify({ board_id: boardId, column_orders: columnOrders }),
    });
  }

  // Cards
  async createCard(data: { column_id: number; title: string; description?: string; language?: string; priority?: string; due_date?: string; assignee_ids?: number[] }) {
    return this.request<any>('/cards', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async getCardDetail(cardId: number) {
    return this.request<any>(`/cards/${cardId}`);
  }

  async updateCard(cardId: number, data: any) {
    return this.request<any>(`/cards/${cardId}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  async moveCard(cardId: number, targetColumnId: number, targetOrder: number) {
    return this.request<any>(`/cards/${cardId}/move`, {
      method: 'POST',
      body: JSON.stringify({ target_column_id: targetColumnId, target_order: targetOrder }),
    });
  }

  async deleteCard(cardId: number) {
    return this.request<any>(`/cards/${cardId}`, {
      method: 'DELETE',
    });
  }

  // Checklists
  async addChecklistItem(cardId: number, title: string) {
    return this.request<any>('/checklists', {
      method: 'POST',
      body: JSON.stringify({ card_id: cardId, title }),
    });
  }

  async toggleChecklistItem(itemId: number) {
    return this.request<any>(`/checklists/${itemId}/toggle`, {
      method: 'PUT',
    });
  }

  async deleteChecklistItem(itemId: number) {
    return this.request<any>(`/checklists/${itemId}`, {
      method: 'DELETE',
    });
  }

  // Comments
  async addComment(cardId: number, text: string, language: string) {
    return this.request<any>('/comments', {
      method: 'POST',
      body: JSON.stringify({ card_id: cardId, text, language }),
    });
  }

  async deleteComment(commentId: number) {
    return this.request<any>(`/comments/${commentId}`, {
      method: 'DELETE',
    });
  }

  // Attachments
  async uploadAttachment(cardId: number, file: File) {
    const formData = new FormData();
    formData.append('card_id', cardId.toString());
    formData.append('file', file);
    return this.request<any>('/attachments', {
      method: 'POST',
      body: formData,
    });
  }

  async deleteAttachment(attachmentId: number) {
    return this.request<any>(`/attachments/${attachmentId}`, {
      method: 'DELETE',
    });
  }

  // Notifications
  async getNotifications(unreadOnly = false) {
    return this.request<{ notifications: any[] }>(`/notifications?unread=${unreadOnly}`);
  }

  async markNotificationsRead(notificationId?: number) {
    return this.request<any>('/notifications', {
      method: 'POST',
      body: JSON.stringify({ notification_id: notificationId }),
    });
  }

  // Users & Departments
  async getUsers(departmentId?: number) {
    const q = departmentId ? `?department_id=${departmentId}` : '';
    return this.request<{ users: any[] }>(`/users${q}`);
  }

  async createUser(data: any) {
    return this.request<any>('/users', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async updateUser(userId: number, data: any) {
    return this.request<any>(`/users/${userId}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  async deleteUser(userId: number) {
    return this.request<any>(`/users/${userId}`, {
      method: 'DELETE',
    });
  }

  async getDepartments() {
    return this.request<{ departments: any[] }>('/departments');
  }

  async createDepartment(name: string) {
    return this.request<any>('/departments', {
      method: 'POST',
      body: JSON.stringify({ name }),
    });
  }

  async updateDepartment(deptId: number, name: string) {
    return this.request<any>(`/departments/${deptId}`, {
      method: 'PUT',
      body: JSON.stringify({ name }),
    });
  }

  async deleteDepartment(deptId: number) {
    return this.request<any>(`/departments/${deptId}`, {
      method: 'DELETE',
    });
  }

  // Reports
  async getAnalytics(period: string, startDate?: string, endDate?: string, departmentId?: number) {
    const query = new URLSearchParams({ period });
    if (startDate) query.append('start_date', startDate);
    if (endDate) query.append('end_date', endDate);
    if (departmentId) query.append('department_id', departmentId.toString());
    return this.request<any>(`/reports/analytics?${query.toString()}`);
  }

  async downloadExport(format: 'xlsx' | 'docx' | 'pdf', period: string, departmentId?: number) {
    const query = new URLSearchParams({ format, period });
    if (departmentId) query.append('department_id', departmentId.toString());

    const token = this.getToken();
    const headers: Record<string, string> = {};
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const res = await fetch(`${API_BASE_URL}/reports/export?${query.toString()}`, {
      headers,
    });

    if (!res.ok) {
      throw new Error(`Export download failed: ${res.status}`);
    }

    const blob = await res.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `report_${period}.${format}`;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
  }

  // Translation helpers
  async convertChinese(text: string, variant: 'zh-Hans' | 'zh-Hant') {
    return this.request<{ text: string; variant: string }>('/translate/convert-chinese', {
      method: 'POST',
      body: JSON.stringify({ text, variant }),
    });
  }

  // Attendance & Time Tracking (Section 4.9)
  async getAttendanceStatus() {
    return this.request<any>('/attendance/status');
  }

  async checkIn(data: { latitude?: number; longitude?: number; accuracy_meters?: number; office_id?: number }) {
    return this.request<{ success: boolean; message: string; record_id: number; timestamp: string; distance_meters: number }>('/attendance/check-in', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async checkOut(data: { latitude?: number; longitude?: number; accuracy_meters?: number; office_id?: number }) {
    return this.request<{ success: boolean; message: string; record_id: number; timestamp: string; distance_meters: number }>('/attendance/check-out', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async leaveAbsence(data: { absence_type: string; reason?: string; comment?: string }) {
    return this.request<{ success: boolean; message: string; absence_id: number; start_time: string }>('/attendance/leave', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async resumeAbsence() {
    return this.request<{ success: boolean; message: string; duration_minutes?: number }>('/attendance/resume', {
      method: 'POST',
    });
  }

  async sendLocationLog(data: { latitude: number; longitude: number; accuracy_meters?: number; source?: string }) {
    return this.request<any>('/attendance/location-log', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async getAttendanceRecords(params?: { user_id?: number; department_id?: number; start_date?: string; end_date?: string }) {
    const query = new URLSearchParams();
    if (params?.user_id) query.append('user_id', params.user_id.toString());
    if (params?.department_id) query.append('department_id', params.department_id.toString());
    if (params?.start_date) query.append('start_date', params.start_date);
    if (params?.end_date) query.append('end_date', params.end_date);
    return this.request<{ records: any[] }>(`/attendance/records?${query.toString()}`);
  }

  async editAttendanceRecord(recordId: number, data: { timestamp: string; edit_reason: string }) {
    return this.request<any>(`/attendance/records/${recordId}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  async getConsent() {
    return this.request<{ is_granted: boolean; consent_version: string; granted_at?: string; revoked_at?: string }>('/attendance/consent');
  }

  async setConsent(data: { is_granted: boolean; consent_version?: string; consent_text?: string }) {
    return this.request<any>('/attendance/consent', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async createDayStatus(data: { user_id?: number; absence_type: string; start_time?: string; end_time?: string; reason?: string; comment?: string }) {
    return this.request<any>('/attendance/day-status', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async getOffices() {
    return this.request<{ offices: any[] }>('/attendance/offices');
  }

  async createOffice(data: any) {
    return this.request<any>('/attendance/offices', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async updateOffice(officeId: number, data: any) {
    return this.request<any>(`/attendance/offices/${officeId}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  async deleteOffice(officeId: number) {
    return this.request<any>(`/attendance/offices/${officeId}`, {
      method: 'DELETE',
    });
  }

  async getSchedules() {
    return this.request<{ schedules: any[] }>('/attendance/schedules');
  }

  async createSchedule(data: any) {
    return this.request<any>('/attendance/schedules', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async getAttendanceTimesheet(year?: number, month?: number, departmentId?: number, userId?: number) {
    const query = new URLSearchParams();
    if (year) query.append('year', year.toString());
    if (month) query.append('month', month.toString());
    if (departmentId) query.append('department_id', departmentId.toString());
    if (userId) query.append('user_id', userId.toString());
    return this.request<any>(`/attendance/reports/timesheet?${query.toString()}`);
  }

  async downloadAttendanceExport(format: 'xlsx' | 'docx' | 'pdf', year?: number, month?: number, departmentId?: number, userId?: number) {
    const query = new URLSearchParams({ format });
    if (year) query.append('year', year.toString());
    if (month) query.append('month', month.toString());
    if (departmentId) query.append('department_id', departmentId.toString());
    if (userId) query.append('user_id', userId.toString());

    const token = this.getToken();
    const headers: Record<string, string> = {};
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const res = await fetch(`${API_BASE_URL}/attendance/reports/export?${query.toString()}`, {
      headers,
    });

    if (!res.ok) {
      throw new Error(`Export download failed: ${res.status}`);
    }

    const blob = await res.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `timesheet_${year || new Date().getFullYear()}_${month || new Date().getMonth() + 1}.${format}`;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
  }
}

export const api = new ApiClient();
