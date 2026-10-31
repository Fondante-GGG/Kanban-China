import type { FinancePaymentRequest, PaymentRequestInput, PaymentRequestCatalog, PaymentProof, PaymentExecutionInput, PaymentExecutionResult, PaymentRequestStatus } from '@/types';
import type { FinancePeriod, FinancePeriodsResponse } from '@/types';
import type { SupplierReturnCorrectionsResponse, SupplierReturnCorrection, SupplierReturnCorrectionInput } from '@/types';
import type { SupplierReturn, SupplierReturnCatalog, SupplierReturnInput, SupplierReturnFinance, SupplierReturnStatus } from '@/types';
import type { StockWriteoff, WriteoffCatalog, WriteoffInput, WriteoffQuery } from '@/types';
import type { WarehouseCatalog, WarehouseInventory, WarehouseMovement, WarehouseReceipt, WarehouseCount, WarehouseExpiry, WarehouseListQuery, WarehouseReceiptInput, WarehouseCountInput, TransferCatalog, TransferInput, TransferQuery, StockTransfer } from '@/types';
import type { KpiTemplate, KpiTask, KpiAssignee, KpiComments, KpiCycle, KpiTemplateItem, ApprovalRequest, Employee, SystemPermission, SystemRole, SystemRoleUser } from '@/types';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8080/api';

class ApiClient {
  private token: string | null = null;

  constructor() {
    if (typeof window !== 'undefined') {
      this.token = localStorage.getItem('kanban_token');
    }
  }

  setToken(token: string | null) {
    const previousToken = this.token;
    this.token = token;
    if (typeof window !== 'undefined') {
      if (token) {
        localStorage.setItem('kanban_token', token);
      } else {
        localStorage.removeItem('kanban_token');
      }
      if (previousToken !== token) window.dispatchEvent(new Event('kanban-auth-change'));
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
        const error = new Error(data.error || 'Server error occurred');
        Object.assign(error, { code: data.code, status: res.status });
        throw error;
      }
      return data;
    }

    if (!res.ok) {
      throw new Error(`HTTP error ${res.status}`);
    }

    return res as unknown as T;
  }

  async getPaymentRequests(params: {limit?:number;offset?:number;q?:string;status?:PaymentRequestStatus;id?:number} = {}, signal?:AbortSignal) { return this.request<{items:FinancePaymentRequest[];count:number;limit:number;offset:number;can_create:boolean}>(`/finance/payment-requests?${this.warehouseQuery(params)}`,{signal}); }
  async getPaymentRequestCatalog(params: {limit?:number;offset?:number;q?:string;payable_id?:number;account_id?:number} = {}, signal?:AbortSignal) { return this.request<PaymentRequestCatalog>(`/finance/payment-requests/catalog?${this.warehouseQuery(params)}`,{signal}); }
  async getPaymentRequest(id:number,signal?:AbortSignal) { return this.request<FinancePaymentRequest>(`/finance/payment-requests/${id}`,{signal}); }
  async createPaymentRequest(data:PaymentRequestInput) { return this.request<FinancePaymentRequest>('/finance/payment-requests',{method:'POST',body:JSON.stringify(data)}); }
  async updatePaymentRequest(id:number,data:Omit<PaymentRequestInput,'request_id'|'request_no'>) { return this.request<FinancePaymentRequest>(`/finance/payment-requests/${id}`,{method:'PATCH',body:JSON.stringify(data)}); }
  async submitPaymentRequest(id:number) { return this.request<FinancePaymentRequest>(`/finance/payment-requests/${id}/submit`,{method:'POST',body:'{}'}); }
  async cancelPaymentRequest(id:number,comment:string) { return this.request<FinancePaymentRequest>(`/finance/payment-requests/${id}/cancel`,{method:'POST',body:JSON.stringify({comment})}); }
  async executePaymentRequest(payableId:number,data:PaymentExecutionInput) { return this.request<PaymentExecutionResult>(`/finance/payables/${payableId}/payments`,{method:'POST',body:JSON.stringify(data)}); }
  async uploadPaymentProof(id:number,file:File) { const data=new FormData();data.append('file',file);return this.request<PaymentProof>(`/finance/payment-requests/${id}/proofs`,{method:'POST',body:data}); }
  async deletePaymentProof(id:number,proofId:number) { return this.request<{id:number}>(`/finance/payment-requests/${id}/proofs/${proofId}`,{method:'DELETE'}); }
  async getPaymentProof(id:number,proofId:number,signal?:AbortSignal):Promise<Blob> { const response=await fetch(`${API_BASE_URL}/finance/payment-requests/${id}/proofs/${proofId}/download`,{headers:{Authorization:`Bearer ${this.getToken()||''}`},signal});if(!response.ok){if(response.status===401)this.setToken(null);const data=await response.json().catch(()=>({}));throw Object.assign(new Error(data.error||`HTTP ${response.status}`),{status:response.status,code:data.code});}return response.blob(); }

  async getFinancePeriods(year: number, signal?: AbortSignal) {
    return this.request<FinancePeriodsResponse>(`/finance/periods?year=${String(year).padStart(4, '0')}`, { signal });
  }
  async closeFinancePeriod(year: number, month: number, reason: string) {
    return this.request<FinancePeriod>(`/finance/periods/${year}/${month}/close`, { method: 'POST', body: JSON.stringify({ reason }) });
  }

  // WMS: permissions, document actions and selectable data come from the server.
  async getSupplierReturnCatalog(params: { warehouse_id?:number; q?:string; receipt_id?:number; limit?:number; offset?:number } = {}) { return this.request<SupplierReturnCatalog>(`/warehouse/returns/catalog?${this.warehouseQuery(params)}`); }
  async getSupplierReturns(params: WarehouseListQuery & { status?: SupplierReturnStatus } = {}) { return this.request<{ items: SupplierReturn[]; count: number }>(`/warehouse/returns?${this.warehouseQuery(params)}`); }
  async createSupplierReturn(data: SupplierReturnInput) { return this.request<{ id: number; status: string }>('/warehouse/returns', { method: 'POST', body: JSON.stringify(data) }); }
  async updateSupplierReturn(id: number, data: SupplierReturnInput) { return this.request<{ id: number; status: string }>(`/warehouse/returns/${id}`, { method: 'PATCH', body: JSON.stringify(data) }); }
  async supplierReturnAction(id: number, action: 'submit' | 'post' | 'cancel', comment = '') { return this.request<{ id: number; status: string }>(`/warehouse/returns/${id}/${action}`, { method: 'POST', body: JSON.stringify({ comment }) }); }
  async reviewSupplierReturn(id: number, decision: 'approve' | 'return' | 'reject', comment: string) { return this.request<{ id: number; status: string }>(`/warehouse/returns/${id}/review`, { method: 'POST', body: JSON.stringify({ decision, comment }) }); }
  async uploadSupplierReturnPhoto(id: number, file: File) { const data = new FormData(); data.append('file', file); return this.request<{ id: number }>(`/warehouse/returns/${id}/photos`, { method: 'POST', body: data }); }
  async deleteSupplierReturnPhoto(id: number, photoId: number) { return this.request<{ id: number }>(`/warehouse/returns/${id}/photos/${photoId}`, { method: 'DELETE' }); }
  async getSupplierReturnPhoto(id: number, photoId: number, signal?: AbortSignal): Promise<Blob> {
    const response = await fetch(`${API_BASE_URL}/warehouse/returns/${id}/photos/${photoId}/download`, { headers: { Authorization: `Bearer ${this.getToken() || ''}` }, signal });
    if (!response.ok) {
      if (response.status === 401) this.setToken(null);
      const data = await response.json().catch(() => ({}));
      throw Object.assign(new Error(data.error || `HTTP ${response.status}`), { status: response.status, code: data.code });
    }
    return response.blob();
  }
  async getSupplierReturnFinancePhoto(id: number, photoId: number, signal?: AbortSignal): Promise<Blob> {
    const response = await fetch(`${API_BASE_URL}/finance/supplier-returns/${id}/photos/${photoId}/download`, { headers: { Authorization: `Bearer ${this.getToken() || ''}` }, signal });
    if (!response.ok) {
      if (response.status === 401) this.setToken(null);
      const data = await response.json().catch(() => ({}));
      throw Object.assign(new Error(data.error || `HTTP ${response.status}`), { status: response.status, code: data.code });
    }
    return response.blob();
  }
  async getSupplierReturnFinance(params: { limit?: number; offset?: number; return_id?:number } = {}) { return this.request<{ items: SupplierReturnFinance[]; count: number }>(`/finance/supplier-returns?${this.warehouseQuery(params)}`); }
  async getSupplierReturnCorrections(id: number, params: { limit?: number; offset?: number; payable_limit?: number; payable_offset?: number; q?: string } = {}, signal?: AbortSignal) {
    return this.request<SupplierReturnCorrectionsResponse>(`/finance/supplier-returns/${id}/corrections?${this.warehouseQuery(params)}`, { signal });
  }
  async confirmSupplierReturnCorrection(id: number, data: SupplierReturnCorrectionInput) {
    return this.request<SupplierReturnCorrection>(`/finance/supplier-returns/${id}/corrections`, { method: 'POST', body: JSON.stringify(data) });
  }
  async getWriteoffCatalog() { return this.request<WriteoffCatalog>('/warehouse/writeoffs/catalog'); }
  async getWriteoffs(params: WriteoffQuery = {}) { return this.request<{ items: StockWriteoff[]; count: number }>(`/warehouse/writeoffs?${this.warehouseQuery(params)}`); }
  async createWriteoff(data: WriteoffInput) { return this.request<{ id: number; status: string }>('/warehouse/writeoffs', { method: 'POST', body: JSON.stringify(data) }); }
  async updateWriteoff(id: number, data: WriteoffInput) { return this.request<{ id: number; status: string }>(`/warehouse/writeoffs/${id}`, { method: 'PATCH', body: JSON.stringify(data) }); }
  async writeoffAction(id: number, action: 'submit' | 'post' | 'cancel', comment = '') { return this.request<{ id: number; status: string }>(`/warehouse/writeoffs/${id}/${action}`, { method: 'POST', body: JSON.stringify({ comment }) }); }
  async reviewWriteoff(id: number, decision: 'approve' | 'return' | 'reject', comment: string) { return this.request<{ id: number; status: string }>(`/warehouse/writeoffs/${id}/review`, { method: 'POST', body: JSON.stringify({ decision, comment }) }); }
  async uploadWriteoffPhoto(id: number, file: File) { const data = new FormData(); data.append('file', file); return this.request<{ id: number }>(`/warehouse/writeoffs/${id}/photos`, { method: 'POST', body: data }); }
  async deleteWriteoffPhoto(id: number, photoId: number) { return this.request<{ id: number }>(`/warehouse/writeoffs/${id}/photos/${photoId}`, { method: 'DELETE' }); }
  async getWriteoffPhoto(id: number, photoId: number, signal?: AbortSignal): Promise<Blob> {
    const response = await fetch(`${API_BASE_URL}/warehouse/writeoffs/${id}/photos/${photoId}/download`, { headers: { Authorization: `Bearer ${this.getToken() || ''}` }, signal });
    if (!response.ok) {
      if (response.status === 401) this.setToken(null);
      const data = await response.json().catch(() => ({}));
      throw Object.assign(new Error(data.error || `HTTP ${response.status}`), { status: response.status, code: data.code });
    }
    return response.blob();
  }
  async getWarehouseCatalog() { return this.request<WarehouseCatalog>('/warehouse/catalog'); }
  async getTransferCatalog() { return this.request<TransferCatalog>('/warehouse/transfers/catalog'); }
  async getTransfers(params: TransferQuery = {}) {
    const query = new URLSearchParams(this.warehouseQuery(params)); if (params.status) query.set('status', params.status);
    return this.request<{ items: StockTransfer[]; count: number }>(`/warehouse/transfers?${query}`);
  }
  async createTransfer(data: TransferInput) { return this.request<{ id: number; status: string }>('/warehouse/transfers', { method: 'POST', body: JSON.stringify(data) }); }
  async updateTransfer(id: number, data: TransferInput) { return this.request<{ id: number; status: string }>(`/warehouse/transfers/${id}`, { method: 'PATCH', body: JSON.stringify(data) }); }
  async transferAction(id: number, action: 'submit' | 'dispatch' | 'receive' | 'cancel', comment = '') {
    return this.request<{ id: number; status: string }>(`/warehouse/transfers/${id}/${action}`, { method: 'POST', body: JSON.stringify({ comment }) });
  }
  async reviewTransfer(id: number, decision: 'approve' | 'return' | 'reject', comment = '') {
    return this.request<{ id: number; status: string }>(`/warehouse/transfers/${id}/review`, { method: 'POST', body: JSON.stringify({ decision, comment }) });
  }
  private warehouseQuery(params: WarehouseListQuery) {
    const query = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => { if (value !== undefined) query.set(key, String(value)); });
    return query.toString();
  }
  async getWarehouseInventory(params: WarehouseListQuery = {}) { return this.request<{ items: WarehouseInventory[]; count: number }>(`/warehouse/inventory?${this.warehouseQuery(params)}`); }
  async getWarehouseMovements(params: WarehouseListQuery = {}) { return this.request<{ items: WarehouseMovement[]; count: number }>(`/warehouse/movements?${this.warehouseQuery(params)}`); }
  async getWarehouseReceipts(params: WarehouseListQuery = {}) { return this.request<{ items: WarehouseReceipt[]; count: number }>(`/warehouse/receipts?${this.warehouseQuery(params)}`); }
  async createWarehouseReceipt(data: WarehouseReceiptInput) { return this.request<{ id: number }>('/warehouse/receipts', { method: 'POST', body: JSON.stringify(data) }); }
  async postWarehouseReceipt(id: number) { return this.request<{ id: number }>(`/warehouse/receipts/${id}/post`, { method: 'POST' }); }
  async getWarehouseCounts(params: WarehouseListQuery = {}) { return this.request<{ items: WarehouseCount[]; count: number }>(`/warehouse/counts?${this.warehouseQuery(params)}`); }
  async createWarehouseCount(data: WarehouseCountInput) { return this.request<{ id: number }>('/warehouse/counts', { method: 'POST', body: JSON.stringify(data) }); }
  async approveWarehouseCount(id: number) { return this.request<{ id: number }>(`/warehouse/counts/${id}/approve`, { method: 'POST' }); }
  async getWarehouseExpiry(warehouseId?: number, days = 30) { return this.request<WarehouseExpiry>(`/warehouse/alerts/expiry?days=${days}${warehouseId ? `&warehouse_id=${warehouseId}` : ''}`); }

  // KPI: action availability is supplied by the authoritative server.
  async getKpiTemplates() { return this.request<{ items: KpiTemplate[] }>('/kpi/templates'); }
  async createKpiTemplate(data: { name: string; position_code: string; cycle: KpiCycle; items: KpiTemplateItem[] }) { return this.request<{ id: number }>('/kpi/templates', { method: 'POST', body: JSON.stringify(data) }); }
  async getKpiAssignees() { return this.request<{ items: KpiAssignee[] }>('/kpi/assignees'); }
  async getKpiTasks(params: { archived?: boolean; year?: number; status?: string; offset?: number; limit?: number } = {}) {
    const query = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => { if (value !== undefined && value !== '') query.set(key, String(value)); });
    return this.request<{ items: KpiTask[]; count: number }>(`/kpi/tasks?${query}`);
  }
  async createKpiTask(data: { template_id: number; employee_id: number; year: number; period: string }) { return this.request<{ id: number }>('/kpi/tasks', { method: 'POST', body: JSON.stringify(data) }); }
  async scoreKpiTask(id: number, data: { stage: 'self' | 'manager'; score: string; comment_ru: string; comment_zh: string; comment_ky: string }) { return this.request<{ id: number }>(`/kpi/tasks/${id}/score`, { method: 'POST', body: JSON.stringify(data) }); }
  async reviewKpiTask(id: number, decision: 'approve' | 'return', comments: KpiComments) { return this.request<{ id: number }>(`/kpi/tasks/${id}/review`, { method: 'POST', body: JSON.stringify({ decision, comment_ru: comments.ru, comment_zh: comments.zh, comment_ky: comments.ky }) }); }
  async acknowledgeKpiTask(id: number) { return this.request<{ id: number }>(`/kpi/tasks/${id}/acknowledge`, { method: 'POST' }); }
  async archiveKpiTask(id: number) { return this.request<{ id: number }>(`/kpi/tasks/${id}/archive`, { method: 'POST' }); }

  // Auth
  async getSuppliers() { return this.request<{items: any[]}>('/procurement/suppliers'); }
  async getSkus() { return this.request<{items: any[]}>('/procurement/skus'); }
  async createSupplier(data: { name_ru: string; name_ky?: string; name_zh?: string }) { return this.request<any>('/procurement/suppliers', { method: 'POST', body: JSON.stringify(data) }); }
  async submitSupplier(id: number) { return this.request<any>(`/procurement/suppliers/${id}/submit`, { method: 'POST' }); }
  async createSku(data: { sku_code: string; name_ru: string; name_ky?: string; name_zh?: string }) { return this.request<any>('/procurement/skus', { method: 'POST', body: JSON.stringify(data) }); }
  async submitSku(id: number) { return this.request<any>(`/procurement/skus/${id}/submit`, { method: 'POST' }); }
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

  async updateInterfaceLanguage(interfaceLanguage: 'ru' | 'ky' | 'zh-Hans' | 'zh-Hant') {
    return this.request<any>('/profile/language', {
      method: 'PATCH',
      body: JSON.stringify({ interface_language: interfaceLanguage }),
    });
  }

  async resetPassword(newPassword: string, userId?: number) {
    return this.request<{ message: string }>('/auth/reset-password', {
      method: 'POST',
      body: JSON.stringify({ new_password: newPassword, user_id: userId }),
    });
  }

  // HR, approvals and independent module permissions. Board roles remain separate.
  async getEmployees(params?: { q?: string; department_id?: number; status?: string; page?: number; page_size?: number }) {
    const query = new URLSearchParams(); Object.entries(params || {}).forEach(([key, value]) => { if (value !== undefined && value !== '') query.set(key, String(value)); });
    return this.request<{ items: Employee[]; page: number; page_size: number; total: number }>(`/hr/employees${query.toString() ? `?${query}` : ''}`);
  }
  async createEmployee(data: Partial<Employee>) { return this.request<Employee>('/hr/employees', { method: 'POST', body: JSON.stringify(data) }); }
  async getEmployee(id: number) { return this.request<Employee>(`/hr/employees/${id}`); }
  async updateEmployee(id: number, data: Partial<Employee>) { return this.request<Employee>(`/hr/employees/${id}`, { method: 'PATCH', body: JSON.stringify(data) }); }
  async submitEmployee(id: number) { return this.request<ApprovalRequest>(`/hr/employees/${id}/submit`, { method: 'POST' }); }
  async submitTermination(id: number, reason: string) { return this.request<ApprovalRequest>(`/hr/employees/${id}/termination/submit`, { method: 'POST', body: JSON.stringify({ reason }) }); }
  async getApprovals(scope: 'assigned' | 'submitted' | 'completed' = 'assigned', status?: string) {
    const query = new URLSearchParams({ scope }); if (status) query.set('status', status);
    return this.request<{ items: ApprovalRequest[]; scope: string }>(`/approvals/inbox?${query}`);
  }
  async actOnApproval(id: number, action: 'approve' | 'reject' | 'return', comment = '') { return this.request<ApprovalRequest>(`/approvals/${id}/actions`, { method: 'POST', body: JSON.stringify({ action, comment }) }); }
  async getSystemRoles() {
    const response = await this.request<{ items: Array<{ id: number; code: string; name: string; description?: string; permission_ids: number[]; permissions: string[] }> }>('/rbac/roles');
    return { items: response.items.map(role => ({ ...role, active: true, permissions: role.permissions.map((code, index) => ({ id: role.permission_ids[index], code, name: code })) })) };
  }
  async getSystemPermissions() {
    return this.request<{ items: SystemPermission[] }>('/rbac/permissions');
  }
  async getSystemRoleUsers() {
    return this.request<{ items: SystemRoleUser[] }>('/rbac/users');
  }
  async createSystemRole(data: { code: string; name: string; description?: string }) { return this.request<SystemRole>('/rbac/roles', { method: 'POST', body: JSON.stringify(data) }); }
  async updateRolePermissions(roleId: number, permission_ids: number[]) { return this.request<SystemRole>(`/rbac/roles/${roleId}/permissions`, { method: 'PUT', body: JSON.stringify({ permission_ids }) }); }
  async assignUserSystemRoles(userId: number, role_ids: number[]) { return this.request<{ user_id: number; role_ids: number[] }>(`/users/${userId}/system-roles`, { method: 'PUT', body: JSON.stringify({ role_ids }) }); }
  async getApproval(id: number, signal?:AbortSignal) { return this.request<ApprovalRequest>(`/approvals/${id}`,{signal}); }
  async getAudit(params: { business_type?: string; business_id?: number } = {}) {
    const query = new URLSearchParams();
    if (params.business_type) query.set('business_type', params.business_type);
    if (params.business_id) query.set('business_id', String(params.business_id));
    return this.request<{ items: Array<{ id: number; action: string; business_type: string; business_id: number; actor_id: number; created_at: string }> }>(`/audit${query.toString() ? `?${query}` : ''}`);
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

  async downloadAttachment(attachmentId: number, fileName: string) {
    const res = await fetch(`${API_BASE_URL}/attachments/${attachmentId}/download`, {
      headers: { Authorization: `Bearer ${this.getToken() || ''}` },
    });
    if (!res.ok) throw new Error('Unable to download attachment');
    const url = URL.createObjectURL(await res.blob());
    const link = document.createElement('a');
    link.href = url;
    link.download = fileName;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
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

  // Finance: company purchases and staff reimbursements
  async getExpenses(params?: Record<string, string | number>) {
    const query = new URLSearchParams();
    Object.entries(params || {}).forEach(([key, value]) => { if (value !== '' && value !== undefined) query.set(key, String(value)); });
    return this.request<{ expenses: any[] }>(`/expenses${query.toString() ? `?${query}` : ''}`);
  }

  async createExpense(data: any) { return this.request<any>('/expenses', { method: 'POST', body: JSON.stringify(data) }); }
  async getExpense(id: number) { return this.request<any>(`/expenses/${id}`); }
  async changeExpenseStatus(id: number, status: string, comment = '') { return this.request<any>(`/expenses/${id}/status`, { method: 'POST', body: JSON.stringify({ status, comment }) }); }
  async uploadExpenseAttachment(id: number, file: File, documentType: string) {
    const data = new FormData(); data.append('file', file); data.append('document_type', documentType);
    return this.request<any>(`/expenses/${id}/attachments`, { method: 'POST', body: data });
  }
  async recordReimbursementPayment(id: number, data: { amount: string; payment_method?: string; transaction_number?: string }) { return this.request<any>(`/expenses/${id}/payment`, { method: 'POST', body: JSON.stringify(data) }); }
  async getExpenseAnalytics(params?: Record<string, string | number>) {
    const query = new URLSearchParams(); Object.entries(params || {}).forEach(([k, v]) => { if (v !== '' && v !== undefined) query.set(k, String(v)); });
    return this.request<any>(`/expenses/analytics${query.toString() ? `?${query}` : ''}`);
  }
  async downloadExpenseAttachment(id: number, fileName: string) {
    const res = await fetch(`${API_BASE_URL}/expense-attachments/${id}/download`, { headers: { Authorization: `Bearer ${this.getToken() || ''}` } });
    if (!res.ok) throw new Error('Не удалось скачать документ');
    const url = URL.createObjectURL(await res.blob()); const link = document.createElement('a'); link.href = url; link.download = fileName; link.click(); URL.revokeObjectURL(url);
  }
  async downloadExpenseExport(format: 'xlsx' | 'docx' | 'pdf') {
    const res = await fetch(`${API_BASE_URL}/expenses/export?format=${format}`, { headers: { Authorization: `Bearer ${this.getToken() || ''}` } });
    if (!res.ok) throw new Error('Не удалось выгрузить отчёт');
    const url = URL.createObjectURL(await res.blob()); const link = document.createElement('a'); link.href = url; link.download = `expenses.${format}`; link.click(); URL.revokeObjectURL(url);
  }
}

export const api = new ApiClient();
