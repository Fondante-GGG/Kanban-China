'use client';

import React, { useState, useEffect } from 'react';
import { User, Department, BoardSummary, LanguageCode, RoleType } from '@/types';
import { 
  translations, 
  localizePersonName, 
  localizeDepartmentName, 
  localizeBoardTitle, 
  localizeRole, 
  localizeDynamicText 
} from '@/lib/i18n';
import { api } from '@/lib/api';
import {
  Users,
  Shield,
  Layers,
  Plus,
  Edit2,
  Trash2,
  KeyRound,
  Building2,
  Search,
  Kanban,
  CheckCircle,
  FolderPlus
} from 'lucide-react';

interface AdminViewProps {
  lang: LanguageCode;
  currentUser: User | null;
  onRefreshBoards: (newBoardId?: number) => void;
}

export const AdminView: React.FC<AdminViewProps> = ({ lang, currentUser, onRefreshBoards }) => {
  const t = translations[lang] || translations.ru;
  const [subTab, setSubTab] = useState<'users' | 'departments' | 'boards' | 'rbac'>('users');

  // Core Data
  const [users, setUsers] = useState<User[]>([]);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [boards, setBoards] = useState<BoardSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchUser, setSearchUser] = useState('');
  const [searchDept, setSearchDept] = useState('');
  const [deptFilter, setDeptFilter] = useState<number | undefined>(undefined);

  // Add/Edit Department Modal
  const [showDeptModal, setShowDeptModal] = useState(false);
  const [editingDeptId, setEditingDeptId] = useState<number | null>(null);
  const [deptName, setDeptName] = useState('');

  // Add/Edit User Modal
  const [showUserModal, setShowUserModal] = useState(false);
  const [editingUserId, setEditingUserId] = useState<number | null>(null);
  const [userFullName, setUserFullName] = useState('');
  const [userEmail, setUserEmail] = useState('');
  const [userPassword, setUserPassword] = useState('');
  const [userPhone, setUserPhone] = useState('');
  const [userRole, setUserRole] = useState<RoleType>('employee');
  const [userDeptId, setUserDeptId] = useState<number | undefined>(undefined);
  const [userBoardId, setUserBoardId] = useState<number | undefined>(undefined);
  const [userLang, setUserLang] = useState('ru');

  // Reset Password Modal
  const [resetPwdUserId, setResetPwdUserId] = useState<number | null>(null);
  const [resetNewPassword, setResetNewPassword] = useState('');

  // Add/Edit Board Modal
  const [showBoardModal, setShowBoardModal] = useState(false);
  const [newBoardTitle, setNewBoardTitle] = useState('');
  const [newBoardDeptId, setNewBoardDeptId] = useState<number | undefined>(undefined);
  const [newBoardTheme, setNewBoardTheme] = useState('gradient-blue');
  const [newBoardManagerId, setNewBoardManagerId] = useState<number | undefined>(undefined);
  const [newBoardEmpIds, setNewBoardEmpIds] = useState<number[]>([]);

  useEffect(() => {
    loadAllData();
  }, [deptFilter]);

  const loadAllData = async () => {
    try {
      setLoading(true);
      const [uRes, dRes, bRes] = await Promise.all([
        api.getUsers(deptFilter),
        api.getDepartments(),
        api.getBoards(),
      ]);
      setUsers(uRes.users);
      setDepartments(dRes.departments);
      setBoards(bRes.boards);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  // --- Department Actions ---
  const handleOpenAddDept = () => {
    setEditingDeptId(null);
    setDeptName('');
    setShowDeptModal(true);
  };

  const handleOpenEditDept = (dept: Department) => {
    setEditingDeptId(dept.id);
    setDeptName(dept.name);
    setShowDeptModal(true);
  };

  const handleSaveDept = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!deptName.trim()) return;
    try {
      if (editingDeptId) {
        await api.updateDepartment(editingDeptId, deptName.trim());
        setShowDeptModal(false);
        setDeptName('');
        await loadAllData();
        onRefreshBoards();
      } else {
        const res = await api.createDepartment(deptName.trim());
        setShowDeptModal(false);
        setDeptName('');
        await loadAllData();
        onRefreshBoards(res?.board_id);
      }
    } catch (err: any) {
      alert(err.message || 'Ошибка сохранения отдела');
    }
  };

  const handleDeleteDept = async (deptId: number) => {
    if (!confirm('Вы уверены, что хотите удалить этот отдел?')) return;
    try {
      await api.deleteDepartment(deptId);
      await loadAllData();
      onRefreshBoards();
    } catch (err: any) {
      alert(err.message || 'Ошибка удаления отдела');
    }
  };

  // --- User Actions ---
  const handleOpenAddUser = () => {
    setEditingUserId(null);
    setUserFullName('');
    setUserEmail('');
    setUserPassword('');
    setUserPhone('');
    setUserRole('employee');
    setUserDeptId(departments[0]?.id);
    setUserBoardId(undefined);
    setUserLang('ru');
    setShowUserModal(true);
  };

  const handleOpenEditUser = (u: User) => {
    setEditingUserId(u.id);
    setUserFullName(u.full_name);
    setUserEmail(u.email);
    setUserPassword('');
    setUserPhone(u.phone || '');
    setUserRole(u.role);
    setUserDeptId(u.department_id || undefined);
    setUserBoardId(u.assigned_board_id || undefined);
    setUserLang(u.interface_language || 'ru');
    setShowUserModal(true);
  };

  const handleSaveUser = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      if (editingUserId) {
        await api.updateUser(editingUserId, {
          full_name: userFullName,
          role: userRole,
          department_id: userDeptId,
          board_id: userBoardId || 0,
          phone: userPhone,
          interface_language: userLang,
          password: userPassword || undefined,
        });
      } else {
        await api.createUser({
          full_name: userFullName,
          email: userEmail,
          password: userPassword || 'password123',
          role: userRole,
          department_id: userDeptId,
          board_id: userBoardId,
          phone: userPhone,
          interface_language: userLang,
        });
      }
      setShowUserModal(false);
      loadAllData();
      onRefreshBoards();
    } catch (err: any) {
      alert(err.message || 'Ошибка сохранения пользователя');
    }
  };

  const handleToggleUserActive = async (u: User) => {
    try {
      await api.updateUser(u.id, { is_active: !u.is_active });
      loadAllData();
    } catch (err: any) {
      alert(err.message || 'Ошибка изменения статуса пользователя');
    }
  };

  const handleDeleteUser = async (userId: number) => {
    if (!confirm(t.confirmDelete)) return;
    try {
      await api.deleteUser(userId);
      loadAllData();
    } catch (err: any) {
      alert(err.message || 'Ошибка удаления пользователя');
    }
  };

  const handleResetPassword = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!resetPwdUserId || !resetNewPassword) return;
    try {
      await api.resetPassword(resetNewPassword, resetPwdUserId);
      setResetPwdUserId(null);
      setResetNewPassword('');
      alert('Пароль успешно обновлён!');
    } catch (err: any) {
      alert(err.message || 'Ошибка обновления пароля');
    }
  };

  // --- Board Actions ---
  const handleCreateBoard = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newBoardTitle.trim()) return;
    try {
      await api.createBoard({
        title: newBoardTitle.trim(),
        department_id: newBoardDeptId,
        background_theme: newBoardTheme,
        manager_id: newBoardManagerId,
        employee_ids: newBoardEmpIds,
      });
      setShowBoardModal(false);
      setNewBoardTitle('');
      loadAllData();
      onRefreshBoards();
    } catch (err: any) {
      alert(err.message || 'Ошибка создания доски');
    }
  };

  const handleDeleteBoard = async (boardId: number) => {
    if (!confirm(t.confirmDelete)) return;
    try {
      await api.deleteBoard(boardId);
      loadAllData();
      onRefreshBoards();
    } catch (err: any) {
      alert(err.message || 'Ошибка удаления доски');
    }
  };

  const filteredUsers = users.filter((u) =>
    u.full_name.toLowerCase().includes(searchUser.toLowerCase()) ||
    u.email.toLowerCase().includes(searchUser.toLowerCase())
  );

  const filteredDepartments = departments.filter((d) =>
    d.name.toLowerCase().includes(searchDept.toLowerCase())
  );

  return (
    <div className="flex-1 p-4 sm:p-8 max-w-7xl mx-auto w-full space-y-6 animate-in fade-in duration-300">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-200 dark:border-slate-800">
        <div className="flex items-center gap-3">
          <div className="h-10 w-10 rounded-xl bg-gradient-to-tr from-slate-700 to-slate-900 flex items-center justify-center text-white shadow">
            <Shield className="w-5 h-5 text-blue-400" />
          </div>
          <div>
            <h1 className="text-xl sm:text-2xl font-black text-black dark:text-white tracking-tight">
              {t.admin}
            </h1>
            <p className="text-xs text-slate-800 dark:text-slate-300 font-semibold">
              Управление пользователями, отделами, канбан-досками и правами доступа
            </p>
          </div>
        </div>

        {/* Subtabs Navigation */}
        <div className="flex items-center p-1 rounded-xl bg-slate-200 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 flex-wrap">
          <button
            onClick={() => setSubTab('users')}
            className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-bold transition ${
              subTab === 'users'
                ? 'bg-white dark:bg-slate-900 text-black dark:text-white shadow-sm'
                : 'text-black dark:text-white hover:opacity-80'
            }`}
          >
            <Users className="w-4 h-4" />
            {t.usersManagement}
          </button>
          <button
            onClick={() => setSubTab('departments')}
            className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-bold transition ${
              subTab === 'departments'
                ? 'bg-white dark:bg-slate-900 text-black dark:text-white shadow-sm'
                : 'text-black dark:text-white hover:opacity-80'
            }`}
          >
            <Building2 className="w-4 h-4" />
            Отделы ({departments.length})
          </button>
          <button
            onClick={() => setSubTab('boards')}
            className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-bold transition ${
              subTab === 'boards'
                ? 'bg-white dark:bg-slate-900 text-black dark:text-white shadow-sm'
                : 'text-black dark:text-white hover:opacity-80'
            }`}
          >
            <Layers className="w-4 h-4" />
            {t.boardsManagement}
          </button>
          <button
            onClick={() => setSubTab('rbac')}
            className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-bold transition ${
              subTab === 'rbac'
                ? 'bg-white dark:bg-slate-900 text-black dark:text-white shadow-sm'
                : 'text-black dark:text-white hover:opacity-80'
            }`}
          >
            <Shield className="w-4 h-4" />
            Матрица прав
          </button>
        </div>
      </div>

      {/* Tab: Departments Management */}
      {subTab === 'departments' && (
        <div className="space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-blue-50/80 dark:bg-blue-950/20 p-4 rounded-2xl border border-blue-200 dark:border-blue-900/40">
            <div>
              <h2 className="text-sm sm:text-base font-black text-black dark:text-white flex items-center gap-2">
                <Building2 className="w-4 h-4 text-blue-700 dark:text-blue-400" />
                Структура отделов компании
              </h2>
              <p className="text-xs text-slate-800 dark:text-slate-300 font-semibold mt-0.5">
                Создавайте отделы для структурирования команд, привязки сотрудников и закрепления канбан-досок.
              </p>
            </div>

            <button
              onClick={handleOpenAddDept}
              className="flex items-center gap-2 px-4 py-2 rounded-xl bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold shadow-md shadow-blue-500/20 transition self-start sm:self-auto"
            >
              <Plus className="w-4 h-4" />
              <span>Создать новый отдел</span>
            </button>
          </div>

          {/* Department Search & Grid */}
          <div className="flex items-center justify-between">
            <div className="relative">
              <Search className="w-3.5 h-3.5 text-black dark:text-white absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                value={searchDept}
                onChange={(e) => setSearchDept(e.target.value)}
                placeholder="Поиск по названию отдела..."
                className="pl-8 pr-3 py-1.5 text-xs font-semibold rounded-xl border border-slate-400 dark:border-slate-700 bg-white dark:bg-slate-800 text-black dark:text-white placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500/20 w-64"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {filteredDepartments.map((dept) => {
              const deptUsers = users.filter((u) => u.department_id === dept.id);
              const deptBoards = boards.filter((b) => b.department_id === dept.id);

              return (
                <div
                  key={dept.id}
                  className="p-5 rounded-2xl bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-800 shadow-sm space-y-4 hover:shadow-md transition relative group"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-2.5">
                      <div className="h-9 w-9 rounded-xl bg-blue-100 dark:bg-blue-950/60 text-blue-700 dark:text-blue-400 flex items-center justify-center font-bold">
                        <Building2 className="w-5 h-5" />
                      </div>
                      <div>
                        <h3 className="font-extrabold text-sm text-black dark:text-white">
                          {localizeDepartmentName(dept.name, lang)}
                        </h3>
                      </div>
                    </div>

                    <div className="flex items-center gap-1 opacity-80 group-hover:opacity-100 transition">
                      <button
                        onClick={() => handleOpenEditDept(dept)}
                        className="p-1.5 rounded-lg text-black hover:text-blue-700 hover:bg-slate-100 dark:hover:bg-slate-800 transition"
                        title="Переименовать отдел"
                      >
                        <Edit2 className="w-3.5 h-3.5" />
                      </button>
                      <button
                        onClick={() => handleDeleteDept(dept.id)}
                        className="p-1.5 rounded-lg text-black hover:text-rose-600 hover:bg-slate-100 dark:hover:bg-slate-800 transition"
                        title="Удалить отдел"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>

                  {/* Stats */}
                  <div className="grid grid-cols-2 gap-2 text-center text-xs py-2.5 bg-slate-100 dark:bg-slate-850 rounded-xl">
                    <div>
                      <span className="text-[10px] text-black dark:text-slate-300 block font-bold">{localizeDynamicText('Сотрудников', lang)}</span>
                      <span className="font-black text-black dark:text-white text-sm">
                        {deptUsers.length}
                      </span>
                    </div>
                    <div>
                      <span className="text-[10px] text-black dark:text-slate-300 block font-bold">{localizeDynamicText('Досок отдела', lang)}</span>
                      <span className="font-black text-black dark:text-white text-sm">
                        {deptBoards.length}
                      </span>
                    </div>
                  </div>

                  {/* Boards in this department preview */}
                  {deptBoards.length > 0 && (
                    <div className="space-y-1">
                      <span className="text-[10px] text-black dark:text-slate-300 uppercase font-black tracking-wider block">
                        {localizeDynamicText('Привязанные доски:', lang)}
                      </span>
                      <div className="flex flex-wrap gap-1">
                        {deptBoards.map((b) => (
                          <span
                            key={b.id}
                            className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[11px] bg-slate-100 dark:bg-slate-800 text-black dark:text-slate-200 border border-slate-300 dark:border-slate-700 font-bold truncate max-w-[200px]"
                          >
                            <Kanban className="w-3 h-3 text-blue-600 flex-shrink-0" />
                            {localizeBoardTitle(b.title, lang, dept.name)}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Tab 1: Users Management */}
      {subTab === 'users' && (
        <div className="space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <div className="relative">
                <Search className="w-3.5 h-3.5 text-black dark:text-white absolute left-3 top-1/2 -translate-y-1/2" />
                <input
                  type="text"
                  value={searchUser}
                  onChange={(e) => setSearchUser(e.target.value)}
                  placeholder="Поиск пользователей..."
                  className="pl-8 pr-3 py-1.5 text-xs font-semibold rounded-xl border border-slate-400 dark:border-slate-700 bg-white dark:bg-slate-800 text-black dark:text-white placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500/20 w-56"
                />
              </div>

              <select
                value={deptFilter || ''}
                onChange={(e) => setDeptFilter(e.target.value ? Number(e.target.value) : undefined)}
                className="text-xs font-bold p-1.5 rounded-xl border border-slate-400 dark:border-slate-700 bg-white dark:bg-slate-800 text-black dark:text-white"
              >
                <option value="">Все отделы</option>
                {departments.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.name}
                  </option>
                ))}
              </select>
            </div>

            <button
              onClick={handleOpenAddUser}
              className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold shadow-sm transition"
            >
              <Plus className="w-4 h-4" />
              <span>{t.addUser}</span>
            </button>
          </div>

          {/* Users Table */}
          <div className="overflow-hidden rounded-2xl border border-slate-300 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-100 dark:bg-slate-850 text-black dark:text-white uppercase tracking-wider font-extrabold border-b border-slate-300 dark:border-slate-800">
                  <tr>
                    <th className="py-3.5 px-4">{t.fullName}</th>
                    <th className="py-3.5 px-3">{t.role}</th>
                    <th className="py-3.5 px-3">{t.department}</th>
                    <th className="py-3.5 px-3">{t.assignedBoard}</th>
                    <th className="py-3.5 px-3 text-center">{t.status}</th>
                    <th className="py-3.5 px-4 text-right">Действия</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200 dark:divide-slate-800/80">
                  {filteredUsers.map((u) => {
                    const isDir = u.role === 'general_director';
                    const isMgr = u.role === 'manager';
                    return (
                      <tr key={u.id} className="hover:bg-slate-50 dark:hover:bg-slate-850/50 transition">
                        <td className="py-3 px-4">
                          <div className="flex items-center gap-2.5">
                            <div className="h-8 w-8 rounded-full bg-slate-900 text-white font-bold text-xs flex items-center justify-center">
                              {u.full_name.charAt(0)}
                            </div>
                            <div>
                              <div className="font-extrabold text-black dark:text-white">{localizePersonName(u.full_name, lang)}</div>
                              <div className="text-[11px] text-slate-800 dark:text-slate-300 font-medium">{u.email}</div>
                              {u.phone && <div className="text-[10px] text-slate-800 dark:text-slate-400 font-semibold">{u.phone}</div>}
                            </div>
                          </div>
                        </td>

                        <td className="py-3 px-3">
                          <span
                            className={`inline-block px-2 py-0.5 rounded-md text-[11px] font-bold border ${
                              isDir
                                ? 'bg-amber-100 text-black dark:bg-amber-950/60 dark:text-white border-amber-300 dark:border-amber-800'
                                : isMgr
                                ? 'bg-blue-100 text-black dark:bg-blue-950/60 dark:text-white border-blue-300 dark:border-blue-800'
                                : 'bg-emerald-100 text-black dark:bg-emerald-950/60 dark:text-white border-emerald-300 dark:border-emerald-800'
                            }`}
                          >
                            {isDir ? t.roleDirector : isMgr ? t.roleManager : t.roleEmployee}
                          </span>
                        </td>

                        <td className="py-3 px-3 text-black dark:text-white font-bold">
                          {localizeDepartmentName(u.department_name, lang) || '—'}
                        </td>

                        <td className="py-3 px-3">
                          {isDir ? (
                            <span className="text-[11px] text-amber-900 dark:text-amber-300 font-extrabold">
                              {localizeDynamicText('Все доски компании', lang)}
                            </span>
                          ) : (
                            <span className="text-[11px] text-black dark:text-white font-bold">
                              {u.assigned_board_title ? localizeBoardTitle(u.assigned_board_title, lang) : localizeDynamicText('— Не назначена —', lang)}
                            </span>
                          )}
                        </td>

                        <td className="py-3 px-3 text-center">
                          <button
                            onClick={() => handleToggleUserActive(u)}
                            className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold border transition ${
                              u.is_active
                                ? 'bg-emerald-100 text-black dark:bg-emerald-950/60 dark:text-white border-emerald-300 hover:bg-rose-100'
                                : 'bg-rose-100 text-black dark:bg-rose-950/60 dark:text-white border-rose-300 hover:bg-emerald-100'
                            }`}
                            title="Нажмите для смены статуса"
                          >
                            {u.is_active ? t.active : t.blocked}
                          </button>
                        </td>

                        <td className="py-3 px-4 text-right">
                          <div className="flex items-center justify-end gap-1.5">
                            <button
                              onClick={() => {
                                setResetPwdUserId(u.id);
                                setResetNewPassword('');
                              }}
                              className="p-1.5 rounded-lg text-black hover:text-blue-700 hover:bg-slate-200 dark:text-slate-300 dark:hover:bg-slate-800 transition"
                              title={t.resetPassword}
                            >
                              <KeyRound className="w-3.5 h-3.5" />
                            </button>
                            <button
                              onClick={() => handleOpenEditUser(u)}
                              className="p-1.5 rounded-lg text-black hover:text-blue-700 hover:bg-slate-200 dark:text-slate-300 dark:hover:bg-slate-800 transition"
                              title="Редактировать"
                            >
                              <Edit2 className="w-3.5 h-3.5" />
                            </button>
                            {currentUser?.id !== u.id && (
                              <button
                                onClick={() => handleDeleteUser(u.id)}
                                className="p-1.5 rounded-lg text-black hover:text-rose-600 hover:bg-slate-200 dark:text-slate-300 dark:hover:bg-slate-800 transition"
                                title={t.delete}
                              >
                                <Trash2 className="w-3.5 h-3.5" />
                              </button>
                            )}
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* Tab 2: Boards Management */}
      {subTab === 'boards' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-black text-black dark:text-white">
              Канбан-доски отделов
            </h2>
            <button
              onClick={() => {
                setNewBoardTitle('');
                setNewBoardDeptId(departments[0]?.id);
                setNewBoardTheme('gradient-blue');
                setNewBoardManagerId(undefined);
                setNewBoardEmpIds([]);
                setShowBoardModal(true);
              }}
              className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold shadow-sm transition"
            >
              <Plus className="w-4 h-4" />
              <span>{t.addBoard}</span>
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {boards.map((b) => (
              <div
                key={b.id}
                className="p-5 rounded-2xl bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-800 shadow-sm space-y-3 hover:shadow-md transition"
              >
                <div className="flex items-start justify-between">
                  <div>
                    <h3 className="font-extrabold text-sm text-black dark:text-white">{localizeBoardTitle(b.title, lang, b.department_name)}</h3>
                    {b.department_name && (
                      <span className="text-xs text-blue-700 dark:text-blue-400 font-extrabold">
                        {localizeDepartmentName(b.department_name, lang)}
                      </span>
                    )}
                  </div>
                  <button
                    onClick={() => handleDeleteBoard(b.id)}
                    className="p-1 text-black hover:text-rose-600 dark:text-slate-400 transition"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>

                <div className="grid grid-cols-3 gap-2 text-center text-xs py-2 bg-slate-100 dark:bg-slate-850 rounded-xl">
                  <div>
                    <span className="text-[10px] text-black dark:text-slate-300 block font-bold">{localizeDynamicText('Разделов', lang)}</span>
                    <span className="font-black text-black dark:text-white text-sm">{b.columns_count}</span>
                  </div>
                  <div>
                    <span className="text-[10px] text-black dark:text-slate-300 block font-bold">{localizeDynamicText('Задач', lang)}</span>
                    <span className="font-black text-black dark:text-white text-sm">{b.cards_count}</span>
                  </div>
                  <div>
                    <span className="text-[10px] text-black dark:text-slate-300 block font-bold">{localizeDynamicText('Участников', lang)}</span>
                    <span className="font-black text-black dark:text-white text-sm">{b.members_count}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Tab 3: Access Matrix Reference */}
      {subTab === 'rbac' && (
        <div className="rounded-2xl border border-slate-300 dark:border-slate-800 bg-white dark:bg-slate-900 p-6 shadow-sm space-y-6">
          <div>
            <h2 className="text-base font-black text-black dark:text-white">
              {localizeDynamicText('Матрица полномочий пользователей', lang)}
            </h2>
            <p className="text-xs text-slate-800 dark:text-slate-300 font-semibold mt-1">
              {localizeDynamicText('Сводная таблица распределения прав и возможностей для сотрудников компании.', lang)}
            </p>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border border-slate-300 dark:border-slate-800 rounded-xl">
              <thead className="bg-slate-100 dark:bg-slate-850 text-black dark:text-white font-extrabold border-b border-slate-300">
                <tr>
                  <th className="p-3">{localizeDynamicText('Возможность / Действие', lang)}</th>
                  <th className="p-3 text-center bg-amber-100/70 dark:bg-amber-950/20 text-amber-950 dark:text-amber-300">
                    {localizeRole('general_director', lang)}
                  </th>
                  <th className="p-3 text-center bg-blue-100/70 dark:bg-blue-950/20 text-blue-950 dark:text-blue-300">
                    {localizeRole('manager', lang)}
                  </th>
                  <th className="p-3 text-center bg-emerald-100/70 dark:bg-emerald-950/20 text-emerald-950 dark:text-emerald-300">
                    {localizeRole('employee', lang)}
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200 dark:divide-slate-800/80">
                <tr>
                  <td className="p-3 font-bold text-black dark:text-white">{localizeDynamicText('Видимость досок', lang)}</td>
                  <td className="p-3 text-center font-black text-emerald-700 dark:text-emerald-400">{localizeDynamicText('Все доски всех отделов', lang)}</td>
                  <td className="p-3 text-center text-black dark:text-slate-200 font-semibold">{localizeDynamicText('Только своего отдела', lang)}</td>
                  <td className="p-3 text-center text-black dark:text-slate-200 font-semibold">{localizeDynamicText('Только своего отдела', lang)}</td>
                </tr>
                <tr>
                  <td className="p-3 font-bold text-black dark:text-white">{localizeDynamicText('Управление разделами (колонками)', lang)}</td>
                  <td className="p-3 text-center text-emerald-700 dark:text-emerald-400 font-black">✓ {localizeDynamicText('Разрешено везде', lang)}</td>
                  <td className="p-3 text-center text-emerald-700 dark:text-emerald-400 font-black">✓ {localizeDynamicText('На своей доске', lang)}</td>
                  <td className="p-3 text-center text-rose-700 dark:text-rose-400 font-black">✗ {localizeDynamicText('Нет доступа', lang)}</td>
                </tr>
                <tr>
                  <td className="p-3 font-bold text-black dark:text-white">{localizeDynamicText('Создание, изменение, удаление задач', lang)}</td>
                  <td className="p-3 text-center text-emerald-700 dark:text-emerald-400 font-black">✓ {localizeDynamicText('Полный доступ', lang)}</td>
                  <td className="p-3 text-center text-emerald-700 dark:text-emerald-400 font-black">✓ {localizeDynamicText('В рамках своего отдела', lang)}</td>
                  <td className="p-3 text-center text-rose-700 dark:text-rose-400 font-black">✗ {localizeDynamicText('Нет доступа', lang)}</td>
                </tr>
                <tr>
                  <td className="p-3 font-bold text-black dark:text-white">{localizeDynamicText('Перемещение карточек по статусам', lang)}</td>
                  <td className="p-3 text-center text-emerald-700 dark:text-emerald-400 font-black">✓ {localizeDynamicText('Разрешено', lang)}</td>
                  <td className="p-3 text-center text-emerald-700 dark:text-emerald-400 font-black">✓ {localizeDynamicText('Разрешено', lang)}</td>
                  <td className="p-3 text-center text-emerald-700 dark:text-emerald-400 font-black">✓ {localizeDynamicText('Разрешено', lang)}</td>
                </tr>
                <tr>
                  <td className="p-3 font-bold text-black dark:text-white">{localizeDynamicText('Обсуждения и комментарии к задачам', lang)}</td>
                  <td className="p-3 text-center text-emerald-700 dark:text-emerald-400 font-black">✓ {localizeDynamicText('Разрешено', lang)}</td>
                  <td className="p-3 text-center text-emerald-700 dark:text-emerald-400 font-black">✓ {localizeDynamicText('Разрешено', lang)}</td>
                  <td className="p-3 text-center text-emerald-700 dark:text-emerald-400 font-black">✓ {localizeDynamicText('Разрешено', lang)}</td>
                </tr>
                <tr>
                  <td className="p-3 font-bold text-black dark:text-white">{localizeDynamicText('Просмотр отчётов и аналитики компании', lang)}</td>
                  <td className="p-3 text-center text-emerald-700 dark:text-emerald-400 font-black">✓ {localizeDynamicText('Доступно', lang)}</td>
                  <td className="p-3 text-center text-rose-700 dark:text-rose-400 font-black">✗ {localizeDynamicText('Нет доступа', lang)}</td>
                  <td className="p-3 text-center text-rose-700 dark:text-rose-400 font-black">✗ {localizeDynamicText('Нет доступа', lang)}</td>
                </tr>
                <tr>
                  <td className="p-3 font-bold text-black dark:text-white">{localizeDynamicText('Управление пользователями и структурой', lang)}</td>
                  <td className="p-3 text-center text-emerald-700 dark:text-emerald-400 font-black">✓ {localizeDynamicText('Доступно', lang)}</td>
                  <td className="p-3 text-center text-rose-700 dark:text-rose-400 font-black">✗ {localizeDynamicText('Нет доступа', lang)}</td>
                  <td className="p-3 text-center text-rose-700 dark:text-rose-400 font-black">✗ {localizeDynamicText('Нет доступа', lang)}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Modal: Create / Edit Department */}
      {showDeptModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/70 backdrop-blur-sm animate-in fade-in">
          <div className="w-full max-w-md rounded-2xl bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-800 p-6 shadow-2xl">
            <h3 className="text-base font-black text-black dark:text-white mb-2 flex items-center gap-2">
              <Building2 className="w-5 h-5 text-blue-700" />
              {editingDeptId ? 'Редактировать отдел' : 'Создать новый отдел'}
            </h3>
            <p className="text-xs text-slate-800 dark:text-slate-300 font-semibold mb-4">
              Укажите название подразделения (например: Отдел логистики, Финансовый отдел, Отдел продаж).
            </p>

            <form onSubmit={handleSaveDept} className="space-y-4">
              <div>
                <label className="text-xs font-bold text-black dark:text-slate-100 uppercase tracking-wider block mb-1">
                  Название отдела *
                </label>
                <input
                  type="text"
                  value={deptName}
                  onChange={(e) => setDeptName(e.target.value)}
                  placeholder="Например: Юридический департамент"
                  className="w-full text-xs sm:text-sm p-3 rounded-xl border border-slate-400 dark:border-slate-700 bg-white dark:bg-slate-800 text-black dark:text-white placeholder:text-slate-500 font-medium focus:outline-none focus:ring-2 focus:ring-blue-500/20"
                  required
                  autoFocus
                />
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowDeptModal(false)}
                  className="px-4 py-2 rounded-xl border border-slate-400 dark:border-slate-700 text-xs font-bold text-black dark:text-slate-200 hover:bg-slate-100 transition"
                >
                  {t.cancel}
                </button>
                <button
                  type="submit"
                  disabled={!deptName.trim()}
                  className="px-4 py-2 rounded-xl bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-xs font-bold shadow-sm transition"
                >
                  {editingDeptId ? 'Сохранить изменения' : 'Создать отдел'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal: Add/Edit User */}
      {showUserModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/70 backdrop-blur-sm animate-in fade-in">
          <div className="w-full max-w-lg rounded-2xl bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-800 p-6 shadow-2xl">
            <h3 className="text-base font-black text-black dark:text-white mb-4">
              {editingUserId ? 'Редактировать пользователя' : t.addUser}
            </h3>

            <form onSubmit={handleSaveUser} className="space-y-4">
              <div>
                <label className="text-xs font-bold text-black dark:text-slate-100 uppercase tracking-wider block mb-1">
                  {t.fullName} *
                </label>
                <input
                  type="text"
                  value={userFullName}
                  onChange={(e) => setUserFullName(e.target.value)}
                  placeholder="Фамилия Имя Отчество"
                  className="w-full text-xs sm:text-sm p-3 rounded-xl border border-slate-400 dark:border-slate-700 bg-white dark:bg-slate-800 text-black dark:text-white placeholder:text-slate-500 font-medium"
                  required
                />
              </div>

              {!editingUserId && (
                <div>
                  <label className="text-xs font-bold text-black dark:text-slate-100 uppercase tracking-wider block mb-1">
                    {t.email} *
                  </label>
                  <input
                    type="email"
                    value={userEmail}
                    onChange={(e) => setUserEmail(e.target.value)}
                    placeholder="name@company.com"
                    className="w-full text-xs sm:text-sm p-3 rounded-xl border border-slate-400 dark:border-slate-700 bg-white dark:bg-slate-800 text-black dark:text-white placeholder:text-slate-500 font-medium"
                    required
                  />
                </div>
              )}

              <div>
                <label className="text-xs font-bold text-black dark:text-slate-100 uppercase tracking-wider block mb-1">
                  {editingUserId ? 'Новый пароль (оставьте пустым если не менять)' : `${t.password} *`}
                </label>
                <input
                  type="password"
                  value={userPassword}
                  onChange={(e) => setUserPassword(e.target.value)}
                  placeholder="Минимум 6 символов"
                  className="w-full text-xs sm:text-sm p-3 rounded-xl border border-slate-400 dark:border-slate-700 bg-white dark:bg-slate-800 text-black dark:text-white placeholder:text-slate-500 font-medium"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-bold text-black dark:text-slate-100 uppercase tracking-wider block mb-1">
                    {t.role} *
                  </label>
                  <select
                    value={userRole}
                    onChange={(e) => setUserRole(e.target.value as RoleType)}
                    className="w-full text-xs p-3 rounded-xl border border-slate-400 dark:border-slate-700 bg-white dark:bg-slate-800 text-black dark:text-white font-medium"
                  >
                    <option value="general_director">{t.roleDirector}</option>
                    <option value="manager">{t.roleManager}</option>
                    <option value="employee">{t.roleEmployee}</option>
                  </select>
                </div>

                <div>
                  <div className="flex items-center justify-between mb-1">
                    <label className="text-xs font-bold text-black dark:text-slate-100 uppercase tracking-wider">
                      {t.department}
                    </label>
                    <button
                      type="button"
                      onClick={() => setShowDeptModal(true)}
                      className="text-[10px] text-blue-700 dark:text-blue-400 font-bold hover:underline flex items-center gap-0.5"
                    >
                      <Plus className="w-2.5 h-2.5" /> Новый отдел
                    </button>
                  </div>
                  <select
                    value={userDeptId || ''}
                    onChange={(e) => setUserDeptId(e.target.value ? Number(e.target.value) : undefined)}
                    className="w-full text-xs p-3 rounded-xl border border-slate-400 dark:border-slate-700 bg-white dark:bg-slate-800 text-black dark:text-white font-medium"
                  >
                    <option value="">Без отдела</option>
                    {departments.map((d) => (
                      <option key={d.id} value={d.id}>
                        {d.name}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              {/* Single Board Assignment Rule */}
              {userRole !== 'general_director' && (
                <div>
                  <label className="text-xs font-bold text-black dark:text-slate-100 uppercase tracking-wider block mb-1">
                    {t.assignedBoard}
                  </label>
                  <select
                    value={userBoardId || ''}
                    onChange={(e) => setUserBoardId(e.target.value ? Number(e.target.value) : undefined)}
                    className="w-full text-xs p-3 rounded-xl border border-slate-400 dark:border-slate-700 bg-white dark:bg-slate-800 text-black dark:text-white font-medium"
                  >
                    <option value="">— {localizeDynamicText('Не привязан к доске', lang)} —</option>
                    {boards.map((b) => (
                      <option key={b.id} value={b.id}>
                        {localizeBoardTitle(b.title, lang, b.department_name)} {b.department_name ? `(${localizeDepartmentName(b.department_name, lang)})` : ''}
                      </option>
                    ))}
                  </select>
                  <p className="text-[11px] text-slate-800 dark:text-slate-300 font-semibold mt-1">
                    {localizeDynamicText('Руководитель и сотрудник могут быть привязаны только к одной доске своего отдела.', lang)}
                  </p>
                </div>
              )}

              <div>
                <label className="text-xs font-bold text-black dark:text-slate-100 uppercase tracking-wider block mb-1">
                  {t.phone}
                </label>
                <input
                  type="text"
                  value={userPhone}
                  onChange={(e) => setUserPhone(e.target.value)}
                  placeholder="+996 555 123456"
                  className="w-full text-xs sm:text-sm p-3 rounded-xl border border-slate-400 dark:border-slate-700 bg-white dark:bg-slate-800 text-black dark:text-white placeholder:text-slate-500 font-medium"
                />
              </div>

              <div className="flex justify-end gap-2 pt-3 border-t border-slate-200 dark:border-slate-800">
                <button
                  type="button"
                  onClick={() => setShowUserModal(false)}
                  className="px-4 py-2 rounded-xl border border-slate-400 dark:border-slate-700 text-xs font-bold text-black dark:text-slate-200 hover:bg-slate-100 transition"
                >
                  {t.cancel}
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 rounded-xl bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold shadow-sm transition"
                >
                  {t.save}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal: Reset Password */}
      {resetPwdUserId !== null && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/70 backdrop-blur-sm animate-in fade-in">
          <div className="w-full max-w-sm rounded-2xl bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-800 p-6 shadow-2xl">
            <h3 className="text-base font-black text-black dark:text-white mb-2">
              {t.resetPassword}
            </h3>
            <form onSubmit={handleResetPassword} className="space-y-4">
              <div>
                <label className="text-xs font-bold text-black dark:text-slate-100 uppercase tracking-wider block mb-1">
                  Новый пароль
                </label>
                <input
                  type="password"
                  value={resetNewPassword}
                  onChange={(e) => setResetNewPassword(e.target.value)}
                  placeholder="Минимум 6 символов"
                  className="w-full text-xs sm:text-sm p-3 rounded-xl border border-slate-400 dark:border-slate-700 bg-white dark:bg-slate-800 text-black dark:text-white placeholder:text-slate-500 font-medium"
                  required
                  autoFocus
                />
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setResetPwdUserId(null)}
                  className="px-4 py-2 rounded-xl border border-slate-400 dark:border-slate-700 text-xs font-bold text-black dark:text-slate-200 hover:bg-slate-100 transition"
                >
                  {t.cancel}
                </button>
                <button
                  type="submit"
                  disabled={!resetNewPassword || resetNewPassword.length < 6}
                  className="px-4 py-2 rounded-xl bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-xs font-bold shadow-sm transition"
                >
                  Сбросить пароль
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal: Create Board */}
      {showBoardModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/70 backdrop-blur-sm animate-in fade-in">
          <div className="w-full max-w-lg rounded-2xl bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-800 p-6 shadow-2xl">
            <h3 className="text-base font-black text-black dark:text-white mb-4">
              {t.addBoard}
            </h3>

            <form onSubmit={handleCreateBoard} className="space-y-4">
              <div>
                <label className="text-xs font-bold text-black dark:text-slate-100 uppercase tracking-wider block mb-1">
                  Название доски *
                </label>
                <input
                  type="text"
                  value={newBoardTitle}
                  onChange={(e) => setNewBoardTitle(e.target.value)}
                  placeholder="Например: Разработка мобильного приложения"
                  className="w-full text-xs sm:text-sm p-3 rounded-xl border border-slate-400 dark:border-slate-700 bg-white dark:bg-slate-800 text-black dark:text-white placeholder:text-slate-500 font-medium"
                  required
                  autoFocus
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <div className="flex items-center justify-between mb-1">
                    <label className="text-xs font-bold text-black dark:text-slate-100 uppercase tracking-wider">
                      Отдел
                    </label>
                    <button
                      type="button"
                      onClick={() => setShowDeptModal(true)}
                      className="text-[10px] text-blue-700 dark:text-blue-400 font-bold hover:underline flex items-center gap-0.5"
                    >
                      <Plus className="w-2.5 h-2.5" /> Новый отдел
                    </button>
                  </div>
                  <select
                    value={newBoardDeptId || ''}
                    onChange={(e) => setNewBoardDeptId(e.target.value ? Number(e.target.value) : undefined)}
                    className="w-full text-xs p-3 rounded-xl border border-slate-400 dark:border-slate-700 bg-white dark:bg-slate-800 text-black dark:text-white font-medium"
                  >
                    <option value="">Без отдела</option>
                    {departments.map((d) => (
                      <option key={d.id} value={d.id}>
                        {d.name}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="text-xs font-bold text-black dark:text-slate-100 uppercase tracking-wider block mb-1">
                    Цветовая тема
                  </label>
                  <select
                    value={newBoardTheme}
                    onChange={(e) => setNewBoardTheme(e.target.value)}
                    className="w-full text-xs p-3 rounded-xl border border-slate-400 dark:border-slate-700 bg-white dark:bg-slate-800 text-black dark:text-white font-medium"
                  >
                    <option value="gradient-blue">Океан (Синий)</option>
                    <option value="gradient-purple">Неон (Пурпур)</option>
                    <option value="gradient-emerald">Изумруд (Зелёный)</option>
                    <option value="gradient-sunset">Закат (Янтарь)</option>
                    <option value="slate-minimal">Минимализм (Серый)</option>
                    <option value="obsidian">Обсидиан (Тёмный)</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="text-xs font-bold text-black dark:text-slate-100 uppercase tracking-wider block mb-1">
                  Назначить руководителя доски
                </label>
                <select
                  value={newBoardManagerId || ''}
                  onChange={(e) => setNewBoardManagerId(e.target.value ? Number(e.target.value) : undefined)}
                  className="w-full text-xs p-3 rounded-xl border border-slate-400 dark:border-slate-700 bg-white dark:bg-slate-800 text-black dark:text-white font-medium"
                >
                  <option value="">— {localizeDynamicText('Выберите руководителя', lang)} —</option>
                  {users.filter((u) => u.role === 'manager').map((m) => (
                    <option key={m.id} value={m.id}>
                      {localizePersonName(m.full_name, lang)} ({m.email})
                    </option>
                  ))}
                </select>
              </div>

              <div className="p-3 bg-blue-50/80 dark:bg-blue-950/30 rounded-xl text-xs text-blue-900 dark:text-blue-300 font-medium border border-blue-200 dark:border-blue-900">
                {localizeDynamicText('При создании новой доски автоматически формируются стандартные разделы («Нужно сделать», «Баги», «В процессе», «На проверке», «Готово») с поддержкой всех языков системы.', lang)}
              </div>

              <div className="flex justify-end gap-2 pt-3 border-t border-slate-200 dark:border-slate-800">
                <button
                  type="button"
                  onClick={() => setShowBoardModal(false)}
                  className="px-4 py-2 rounded-xl border border-slate-400 dark:border-slate-700 text-xs font-bold text-black dark:text-slate-200 hover:bg-slate-100 transition"
                >
                  {t.cancel}
                </button>
                <button
                  type="submit"
                  disabled={!newBoardTitle.trim()}
                  className="px-4 py-2 rounded-xl bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-xs font-bold shadow-sm transition"
                >
                  {t.addBoard}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
