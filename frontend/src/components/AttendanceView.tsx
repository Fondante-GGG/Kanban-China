'use client';

import React, { useState, useEffect } from 'react';
import {
  User,
  LanguageCode,
  AttendanceRecord,
  TimesheetReport,
  TimesheetEmployee,
  Office,
  WorkSchedule,
} from '@/types';
import {
  translations,
  localizePersonName,
  localizeDepartmentName,
  localizeRole,
  localizeDynamicText,
} from '@/lib/i18n';
import { api } from '@/lib/api';
import {
  Calendar,
  Clock,
  Download,
  Filter,
  Search,
  UserCheck,
  AlertTriangle,
  Building2,
  MapPin,
  Edit2,
  Plus,
  Trash2,
  FileSpreadsheet,
  FileText,
  FileDown,
  ChevronLeft,
  ChevronRight,
  ShieldCheck,
  CheckCircle2,
  XCircle,
  Briefcase,
  Users
} from 'lucide-react';

interface AttendanceViewProps {
  currentUser: User;
  lang: LanguageCode;
}

export const AttendanceView: React.FC<AttendanceViewProps> = ({ currentUser, lang }) => {
  const t = translations[lang] || translations.ru;
  const isManagerOrDirector = currentUser.role === 'general_director' || currentUser.role === 'manager';
  const isDirector = currentUser.role === 'general_director';

  const [activeSubTab, setActiveSubTab] = useState<'my' | 'team' | 'settings'>(
    isManagerOrDirector ? 'team' : 'my'
  );

  // Month & Year state
  const currentDate = new Date();
  const [selectedYear, setSelectedYear] = useState(currentDate.getFullYear());
  const [selectedMonth, setSelectedMonth] = useState(currentDate.getMonth() + 1);

  // My Records state
  const [myRecords, setMyRecords] = useState<AttendanceRecord[]>([]);
  const [loadingMyRecords, setLoadingMyRecords] = useState(false);

  // Team Timesheet state
  const [timesheetData, setTimesheetData] = useState<TimesheetReport | null>(null);
  const [loadingTimesheet, setLoadingTimesheet] = useState(false);
  const [searchEmployee, setSearchEmployee] = useState('');
  const [selectedDeptId, setSelectedDeptId] = useState<number | null>(null);
  const [exportingFormat, setExportingFormat] = useState<string | null>(null);

  // Edit Record Modal state
  const [editingRecord, setEditingRecord] = useState<AttendanceRecord | null>(null);
  const [editTimestamp, setEditTimestamp] = useState('');
  const [editReason, setEditReason] = useState('');
  const [savingEdit, setSavingEdit] = useState(false);

  // Day Status Modal state
  const [showDayStatusModal, setShowDayStatusModal] = useState(false);
  const [dayStatusUserId, setDayStatusUserId] = useState<number>(currentUser.id);
  const [dayStatusType, setDayStatusType] = useState<'vacation' | 'sick_leave' | 'business_trip' | 'day_off'>('vacation');
  const [dayStatusStart, setDayStatusStart] = useState(new Date().toISOString().slice(0, 10));
  const [dayStatusEnd, setDayStatusEnd] = useState(new Date().toISOString().slice(0, 10));
  const [dayStatusReason, setDayStatusReason] = useState('');

  // Offices & Schedules state
  const [offices, setOffices] = useState<Office[]>([]);
  const [schedules, setSchedules] = useState<WorkSchedule[]>([]);
  const [showOfficeModal, setShowOfficeModal] = useState(false);
  const [officeForm, setOfficeForm] = useState<Partial<Office>>({
    name: '',
    address: '',
    latitude: 42.8746,
    longitude: 74.5698,
    radius_meters: 100,
    ip_subnet: '',
    is_ip_check_enabled: false,
  });

  useEffect(() => {
    if (activeSubTab === 'my') {
      loadMyRecords();
    } else if (activeSubTab === 'team') {
      loadTimesheet();
    } else if (activeSubTab === 'settings') {
      loadOfficesAndSchedules();
    }
  }, [activeSubTab, selectedYear, selectedMonth, selectedDeptId]);

  const loadMyRecords = async () => {
    try {
      setLoadingMyRecords(true);
      const res = await api.getAttendanceRecords({ user_id: currentUser.id });
      setMyRecords(res.records);
    } catch (err) {
      console.error(err);
    } finally {
      setLoadingMyRecords(false);
    }
  };

  const loadTimesheet = async () => {
    try {
      setLoadingTimesheet(true);
      const res = await api.getAttendanceTimesheet(
        selectedYear,
        selectedMonth,
        selectedDeptId || undefined
      );
      setTimesheetData(res);
    } catch (err) {
      console.error(err);
    } finally {
      setLoadingTimesheet(false);
    }
  };

  const loadOfficesAndSchedules = async () => {
    try {
      const [officesRes, schedsRes] = await Promise.all([
        api.getOffices(),
        api.getSchedules(),
      ]);
      setOffices(officesRes.offices);
      setSchedules(schedsRes.schedules);
    } catch (err) {
      console.error(err);
    }
  };

  const handleExport = async (format: 'xlsx' | 'docx' | 'pdf') => {
    try {
      setExportingFormat(format);
      await api.downloadAttendanceExport(
        format,
        selectedYear,
        selectedMonth,
        selectedDeptId || undefined
      );
    } catch (err: any) {
      alert(err.message || 'Ошибка экспорта табеля');
    } finally {
      setExportingFormat(null);
    }
  };

  const handleSaveEditRecord = async () => {
    if (!editingRecord) return;
    if (!editReason.trim()) {
      alert(t.mandatoryReason || 'Обязательно укажите причину правки');
      return;
    }
    try {
      setSavingEdit(true);
      await api.editAttendanceRecord(editingRecord.id, {
        timestamp: editTimestamp,
        edit_reason: editReason,
      });
      setEditingRecord(null);
      setEditReason('');
      if (activeSubTab === 'my') loadMyRecords();
      if (activeSubTab === 'team') loadTimesheet();
    } catch (err: any) {
      alert(err.message || 'Ошибка редактирования отметки');
    } finally {
      setSavingEdit(false);
    }
  };

  const handleSaveDayStatus = async () => {
    try {
      await api.createDayStatus({
        user_id: dayStatusUserId,
        absence_type: dayStatusType,
        start_time: `${dayStatusStart}T09:00:00`,
        end_time: `${dayStatusEnd}T18:00:00`,
        reason: dayStatusReason,
      });
      setShowDayStatusModal(false);
      setDayStatusReason('');
      if (activeSubTab === 'my') loadMyRecords();
      if (activeSubTab === 'team') loadTimesheet();
    } catch (err: any) {
      alert(err.message || 'Ошибка назначения статуса');
    }
  };

  const handleDetectCoordinates = () => {
    if ('geolocation' in navigator) {
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          setOfficeForm((prev) => ({
            ...prev,
            latitude: Number(pos.coords.latitude.toFixed(6)),
            longitude: Number(pos.coords.longitude.toFixed(6)),
          }));
        },
        (err) => alert(`Ошибка GPS: ${err.message}`)
      );
    } else {
      alert('Геолокация не поддерживается вашим браузером');
    }
  };

  const handleSaveOffice = async () => {
    if (!officeForm.name?.trim()) {
      alert('Укажите название офиса');
      return;
    }
    try {
      if (officeForm.id) {
        await api.updateOffice(officeForm.id, officeForm);
      } else {
        await api.createOffice(officeForm);
      }
      setShowOfficeModal(false);
      loadOfficesAndSchedules();
    } catch (err: any) {
      alert(err.message);
    }
  };

  const handleDeleteOffice = async (officeId: number) => {
    if (!confirm('Вы уверены, что хотите удалить офис?')) return;
    try {
      await api.deleteOffice(officeId);
      loadOfficesAndSchedules();
    } catch (err: any) {
      alert(err.message);
    }
  };

  const handlePrevMonth = () => {
    if (selectedMonth === 1) {
      setSelectedMonth(12);
      setSelectedYear((y) => y - 1);
    } else {
      setSelectedMonth((m) => m - 1);
    }
  };

  const handleNextMonth = () => {
    if (selectedMonth === 12) {
      setSelectedMonth(1);
      setSelectedYear((y) => y + 1);
    } else {
      setSelectedMonth((m) => m + 1);
    }
  };

  const filteredEmployees =
    timesheetData?.employees.filter(
      (emp) =>
        emp.full_name.toLowerCase().includes(searchEmployee.toLowerCase()) ||
        emp.department_name.toLowerCase().includes(searchEmployee.toLowerCase()) ||
        emp.email.toLowerCase().includes(searchEmployee.toLowerCase())
    ) || [];

  return (
    <div className="flex-1 p-4 sm:p-8 max-w-7xl mx-auto w-full space-y-6 animate-in fade-in duration-300">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-slate-200 dark:border-slate-800">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="h-10 w-10 rounded-xl bg-gradient-to-tr from-emerald-600 to-teal-600 flex items-center justify-center text-white shadow-md shadow-emerald-500/20 font-bold">
              <Clock className="w-5 h-5" />
            </div>
            <div>
              <h1 className="text-xl font-extrabold text-black dark:text-white">
                {t.attendance}
              </h1>
              <p className="text-xs text-slate-800 dark:text-slate-300 font-medium">
                Контроль рабочего времени, геопозиции и табель посещаемости (ТЗ п. 4.9)
              </p>
            </div>
          </div>
        </div>

        {/* SubTabs */}
        <div className="flex items-center gap-1.5 p-1 bg-slate-200 dark:bg-slate-800 rounded-xl border border-slate-300 dark:border-slate-700">
          <button
            onClick={() => setActiveSubTab('my')}
            className={`px-3 py-1.5 rounded-lg text-xs font-bold transition ${
              activeSubTab === 'my'
                ? 'bg-white dark:bg-slate-900 text-black dark:text-white shadow-sm'
                : 'text-slate-700 dark:text-slate-300 hover:text-black dark:hover:text-white'
            }`}
          >
            {t.myAttendance}
          </button>

          {isManagerOrDirector && (
            <button
              onClick={() => setActiveSubTab('team')}
              className={`px-3 py-1.5 rounded-lg text-xs font-bold transition ${
                activeSubTab === 'team'
                  ? 'bg-white dark:bg-slate-900 text-black dark:text-white shadow-sm'
                  : 'text-slate-700 dark:text-slate-300 hover:text-black dark:hover:text-white'
              }`}
            >
              {t.teamTimesheet}
            </button>
          )}

          {isDirector && (
            <button
              onClick={() => setActiveSubTab('settings')}
              className={`px-3 py-1.5 rounded-lg text-xs font-bold transition ${
                activeSubTab === 'settings'
                  ? 'bg-white dark:bg-slate-900 text-black dark:text-white shadow-sm'
                  : 'text-slate-700 dark:text-slate-300 hover:text-black dark:hover:text-white'
              }`}
            >
              {t.officesAndSchedules}
            </button>
          )}
        </div>
      </div>

      {/* SUBTAB 1: MY ATTENDANCE */}
      {activeSubTab === 'my' && (
        <div className="space-y-6">
          <div className="flex flex-wrap items-center justify-between gap-3 bg-white dark:bg-slate-900 p-4 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm">
            <div>
              <h3 className="text-sm font-bold text-black dark:text-white">История моих отметок</h3>
              <p className="text-xs text-slate-800 dark:text-slate-300 font-medium">
                Фиксация времени, геолокации и проверок в радиусе офиса
              </p>
            </div>
            <button
              onClick={() => {
                setDayStatusUserId(currentUser.id);
                setShowDayStatusModal(true);
              }}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-blue-600 hover:bg-blue-500 text-white text-xs font-bold shadow-sm transition"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>Запросить статус дня (Отпуск/Больничный)</span>
            </button>
          </div>

          {/* Records Table */}
          <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="bg-slate-100 dark:bg-slate-800/80 border-b border-slate-200 dark:border-slate-700 text-black dark:text-white font-bold">
                    <th className="py-3 px-4">Тип отметки</th>
                    <th className="py-3 px-4">Время и дата</th>
                    <th className="py-3 px-4">Офис</th>
                    <th className="py-3 px-4 text-center">Проверка радиуса</th>
                    <th className="py-3 px-4 text-center">Статус</th>
                    <th className="py-3 px-4">Примечания</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200 dark:divide-slate-800">
                  {loadingMyRecords ? (
                    <tr>
                      <td colSpan={6} className="py-8 text-center text-slate-400 font-semibold">
                        Загрузка отметок...
                      </td>
                    </tr>
                  ) : myRecords.length === 0 ? (
                    <tr>
                      <td colSpan={6} className="py-8 text-center text-slate-400 font-semibold">
                        У вас пока нет отметок посещаемости
                      </td>
                    </tr>
                  ) : (
                    myRecords.map((r) => (
                      <tr key={r.id} className="hover:bg-slate-50 dark:hover:bg-slate-800/50 transition">
                        <td className="py-3 px-4 font-bold">
                          <span
                            className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-bold ${
                              r.record_type === 'check_in'
                                ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300'
                                : 'bg-rose-100 text-rose-800 dark:bg-rose-950/60 dark:text-rose-300'
                            }`}
                          >
                            {r.record_type === 'check_in' ? t.checkIn : t.checkOut}
                          </span>
                        </td>
                        <td className="py-3 px-4 font-semibold text-slate-900 dark:text-slate-100">
                          {new Date(r.timestamp).toLocaleString([], {
                            day: '2-digit',
                            month: '2-digit',
                            year: 'numeric',
                            hour: '2-digit',
                            minute: '2-digit',
                          })}
                          {r.is_edited && (
                            <span className="ml-2 text-[10px] font-bold text-amber-600 bg-amber-50 dark:bg-amber-950/40 px-1.5 py-0.5 rounded border border-amber-300">
                              Исправлено: {r.edited_by_name}
                            </span>
                          )}
                        </td>
                        <td className="py-3 px-4 text-slate-700 dark:text-slate-300 font-medium">
                          {r.office_name}
                        </td>
                        <td className="py-3 px-4 text-center">
                          {r.is_within_radius ? (
                            <span className="inline-flex items-center gap-1 text-emerald-600 font-bold">
                              <CheckCircle2 className="w-4 h-4" /> В радиусе
                            </span>
                          ) : (
                            <span className="inline-flex items-center gap-1 text-rose-600 font-bold">
                              <XCircle className="w-4 h-4" /> Вне зоны
                            </span>
                          )}
                        </td>
                        <td className="py-3 px-4 text-center font-bold">
                          {r.verification_result === 'verified' && (
                            <span className="text-emerald-600">Подтверждено</span>
                          )}
                          {r.verification_result === 'rejected' && (
                            <span className="text-rose-600">Отклонено</span>
                          )}
                          {r.verification_result === 'manual_override' && (
                            <span className="text-amber-600">Ручная правка</span>
                          )}
                        </td>
                        <td className="py-3 px-4 text-slate-500 font-medium text-[11px] max-w-xs truncate">
                          {r.edit_reason || r.rejection_reason || '—'}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* SUBTAB 2: TEAM TIMESHEET (MANAGERS & DIRECTOR) */}
      {activeSubTab === 'team' && isManagerOrDirector && (
        <div className="space-y-6">
          {/* Controls: Month selector, Filters, Export Buttons */}
          <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 bg-white dark:bg-slate-900 p-4 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm">
            {/* Month & Year Navigator */}
            <div className="flex items-center gap-2">
              <button
                onClick={handlePrevMonth}
                className="p-1.5 rounded-lg border border-slate-300 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-800 transition"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
              <div className="px-3 py-1 font-extrabold text-sm text-black dark:text-white min-w-[130px] text-center">
                {new Date(selectedYear, selectedMonth - 1, 1).toLocaleString(lang === 'ky' ? 'ky-KG' : lang.startsWith('zh') ? 'zh-CN' : 'ru-RU', {
                  month: 'long',
                  year: 'numeric',
                })}
              </div>
              <button
                onClick={handleNextMonth}
                className="p-1.5 rounded-lg border border-slate-300 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-800 transition"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>

            {/* Search Employee */}
            <div className="flex-1 max-w-xs relative">
              <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
              <input
                type="text"
                placeholder="Поиск сотрудника..."
                value={searchEmployee}
                onChange={(e) => setSearchEmployee(e.target.value)}
                className="w-full pl-9 pr-3 py-1.5 text-xs rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-black dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            {/* Export Buttons: Excel, PDF, Word */}
            <div className="flex items-center gap-2">
              <button
                onClick={() => handleExport('xlsx')}
                disabled={Boolean(exportingFormat)}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-emerald-50 dark:bg-emerald-950/50 text-emerald-900 dark:text-emerald-200 border border-emerald-300 dark:border-emerald-800 text-xs font-bold hover:bg-emerald-100 dark:hover:bg-emerald-900/60 active:scale-95 transition"
              >
                <FileSpreadsheet className="w-3.5 h-3.5 text-emerald-600" />
                <span>Excel (.xlsx)</span>
              </button>

              <button
                onClick={() => handleExport('pdf')}
                disabled={Boolean(exportingFormat)}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-rose-50 dark:bg-rose-950/50 text-rose-900 dark:text-rose-200 border border-rose-300 dark:border-rose-800 text-xs font-bold hover:bg-rose-100 dark:hover:bg-rose-900/60 active:scale-95 transition"
              >
                <FileDown className="w-3.5 h-3.5 text-rose-600" />
                <span>PDF (.pdf)</span>
              </button>

              <button
                onClick={() => handleExport('docx')}
                disabled={Boolean(exportingFormat)}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-blue-50 dark:bg-blue-950/50 text-blue-900 dark:text-blue-200 border border-blue-300 dark:border-blue-800 text-xs font-bold hover:bg-blue-100 dark:hover:bg-blue-900/60 active:scale-95 transition"
              >
                <FileText className="w-3.5 h-3.5 text-blue-600" />
                <span>Word (.docx)</span>
              </button>

              <button
                onClick={() => setShowDayStatusModal(true)}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-900 text-white dark:bg-white dark:text-slate-900 text-xs font-bold hover:opacity-90 active:scale-95 transition"
              >
                <Plus className="w-3.5 h-3.5" />
                <span>Статус дня</span>
              </button>
            </div>
          </div>

          {/* Department Summary Highlights */}
          {timesheetData?.departments && timesheetData.departments.length > 0 && (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              {timesheetData.departments.map((dept) => (
                <div
                  key={dept.department_name}
                  className="bg-white dark:bg-slate-900 p-4 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm"
                >
                  <div className="flex items-center justify-between pb-2 border-b border-slate-100 dark:border-slate-800">
                    <span className="font-extrabold text-xs text-black dark:text-white truncate">
                      {localizeDepartmentName(dept.department_name, lang)}
                    </span>
                    <span className="text-[10px] font-bold text-slate-500">
                      {dept.employees_count} сотр.
                    </span>
                  </div>
                  <div className="grid grid-cols-2 gap-2 mt-3 text-xs">
                    <div>
                      <span className="text-[10px] text-slate-500 font-semibold block">Отработано:</span>
                      <span className="text-sm font-extrabold text-blue-600">{dept.total_worked_hours} ч</span>
                    </div>
                    <div>
                      <span className="text-[10px] text-slate-500 font-semibold block">Опозданий:</span>
                      <span className="text-sm font-extrabold text-amber-600">
                        {dept.total_late_count} ({dept.total_late_minutes}м)
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Monthly Timesheet Table */}
          <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="bg-slate-100 dark:bg-slate-800/80 border-b border-slate-200 dark:border-slate-700 text-black dark:text-white font-bold">
                    <th className="py-3 px-4">Сотрудник</th>
                    <th className="py-3 px-4">Отдел</th>
                    <th className="py-3 px-3 text-center">Отработано дней</th>
                    <th className="py-3 px-3 text-center">Всего часов</th>
                    <th className="py-3 px-3 text-center">Опоздания (раз/мин)</th>
                    <th className="py-3 px-3 text-center">Ранние уходы</th>
                    <th className="py-3 px-3 text-center">Отлучки (личн./дела)</th>
                    <th className="py-3 px-3 text-center">Отпуск / Больн.</th>
                    <th className="py-3 px-4 text-center">Действие</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200 dark:divide-slate-800">
                  {loadingTimesheet ? (
                    <tr>
                      <td colSpan={9} className="py-8 text-center text-slate-400 font-semibold">
                        Формирование табеля...
                      </td>
                    </tr>
                  ) : filteredEmployees.length === 0 ? (
                    <tr>
                      <td colSpan={9} className="py-8 text-center text-slate-400 font-semibold">
                        Сотрудники не найдены
                      </td>
                    </tr>
                  ) : (
                    filteredEmployees.map((emp) => (
                      <tr key={emp.user_id} className="hover:bg-slate-50 dark:hover:bg-slate-800/50 transition">
                        <td className="py-3 px-4 font-bold text-black dark:text-white">
                          <div>{localizePersonName(emp.full_name, lang)}</div>
                          <div className="text-[10px] text-slate-500 font-normal">{emp.email}</div>
                        </td>
                        <td className="py-3 px-4 text-slate-700 dark:text-slate-300 font-medium">
                          {localizeDepartmentName(emp.department_name, lang)}
                        </td>
                        <td className="py-3 px-3 text-center font-bold text-slate-900 dark:text-slate-100">
                          {emp.days_worked}
                        </td>
                        <td className="py-3 px-3 text-center font-extrabold text-blue-600">
                          {emp.total_worked_hours} ч
                        </td>
                        <td className="py-3 px-3 text-center font-bold">
                          {emp.late_count > 0 ? (
                            <span className="text-amber-600">
                              {emp.late_count} ({emp.total_late_minutes} мин)
                            </span>
                          ) : (
                            <span className="text-slate-400">0</span>
                          )}
                        </td>
                        <td className="py-3 px-3 text-center font-bold">
                          {emp.early_count > 0 ? (
                            <span className="text-rose-600">{emp.early_count}</span>
                          ) : (
                            <span className="text-slate-400">0</span>
                          )}
                        </td>
                        <td className="py-3 px-3 text-center font-medium text-slate-700 dark:text-slate-300">
                          {emp.personal_hours}ч / {emp.business_hours}ч
                        </td>
                        <td className="py-3 px-3 text-center font-semibold text-slate-700 dark:text-slate-300">
                          {emp.vacation_days > 0 || emp.sick_days > 0
                            ? `${emp.vacation_days} дн. / ${emp.sick_days} дн.`
                            : '—'}
                        </td>
                        <td className="py-3 px-4 text-center">
                          <button
                            onClick={() => {
                              // Find recent record to edit
                              api.getAttendanceRecords({ user_id: emp.user_id }).then((res) => {
                                if (res.records.length > 0) {
                                  const r = res.records[0];
                                  setEditingRecord(r);
                                  setEditTimestamp(new Date(r.timestamp).toISOString().slice(0, 16));
                                } else {
                                  alert('У сотрудника нет сохранённых отметок для правки');
                                }
                              });
                            }}
                            className="inline-flex items-center gap-1 text-[11px] font-bold text-blue-600 hover:text-blue-500 bg-blue-50 dark:bg-blue-950/40 px-2 py-1 rounded-lg border border-blue-200 dark:border-blue-800 transition"
                            title="Исправить отметку с обязательной причиной"
                          >
                            <Edit2 className="w-3 h-3" />
                            <span>{t.editRecord}</span>
                          </button>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* SUBTAB 3: OFFICES AND SCHEDULES (DIRECTOR & ADMIN ONLY) */}
      {activeSubTab === 'settings' && isDirector && (
        <div className="space-y-6">
          {/* Offices List */}
          <div className="bg-white dark:bg-slate-900 p-6 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-200 dark:border-slate-800">
              <div className="flex items-center gap-2">
                <MapPin className="w-5 h-5 text-blue-600" />
                <h3 className="text-base font-bold text-black dark:text-white">
                  Офисы компании и геозоны (радиусы отметки)
                </h3>
              </div>
              <button
                onClick={() => {
                  setOfficeForm({
                    name: '',
                    address: '',
                    latitude: 42.8746,
                    longitude: 74.5698,
                    radius_meters: 100,
                    ip_subnet: '',
                    is_ip_check_enabled: false,
                  });
                  setShowOfficeModal(true);
                }}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-blue-600 hover:bg-blue-500 text-white text-xs font-bold shadow-sm transition"
              >
                <Plus className="w-3.5 h-3.5" />
                <span>Добавить офис</span>
              </button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {offices.map((off) => (
                <div
                  key={off.id}
                  className="bg-slate-50 dark:bg-slate-800/60 p-4 rounded-xl border border-slate-200 dark:border-slate-700 flex flex-col justify-between space-y-3"
                >
                  <div>
                    <div className="flex items-start justify-between">
                      <h4 className="font-extrabold text-sm text-black dark:text-white">{off.name}</h4>
                      <span className="text-[10px] font-bold bg-blue-100 text-blue-800 dark:bg-blue-950 dark:text-blue-300 px-2 py-0.5 rounded-md">
                        R = {off.radius_meters} м
                      </span>
                    </div>
                    {off.address && (
                      <p className="text-xs text-slate-500 mt-1 font-medium">{off.address}</p>
                    )}
                    <div className="text-[11px] text-slate-700 dark:text-slate-300 font-mono mt-2">
                      GPS: {off.latitude.toFixed(5)}, {off.longitude.toFixed(5)}
                    </div>
                    {off.is_ip_check_enabled && (
                      <div className="text-[10px] text-emerald-600 font-bold mt-1">
                        Проверка IP включена ({off.ip_subnet || 'без маски'})
                      </div>
                    )}
                  </div>

                  <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-200 dark:border-slate-700">
                    <button
                      onClick={() => {
                        setOfficeForm(off);
                        setShowOfficeModal(true);
                      }}
                      className="p-1.5 text-slate-600 dark:text-slate-300 hover:text-blue-600 transition"
                      title="Редактировать"
                    >
                      <Edit2 className="w-3.5 h-3.5" />
                    </button>
                    <button
                      onClick={() => handleDeleteOffice(off.id)}
                      className="p-1.5 text-slate-600 dark:text-slate-300 hover:text-rose-600 transition"
                      title="Удалить"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Schedules List */}
          <div className="bg-white dark:bg-slate-900 p-6 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-200 dark:border-slate-800">
              <div className="flex items-center gap-2">
                <Briefcase className="w-5 h-5 text-indigo-600" />
                <h3 className="text-base font-bold text-black dark:text-white">
                  Рабочие графики (часовой пояс: Asia/Bishkek)
                </h3>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {schedules.map((sc) => (
                <div
                  key={sc.id}
                  className="bg-slate-50 dark:bg-slate-800/60 p-4 rounded-xl border border-slate-200 dark:border-slate-700 space-y-2"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-extrabold text-sm text-black dark:text-white">{sc.name}</span>
                    <span className="text-[10px] font-bold text-emerald-600 bg-emerald-50 dark:bg-emerald-950/40 px-2 py-0.5 rounded border border-emerald-300">
                      Активен
                    </span>
                  </div>
                  <div className="text-xs text-slate-700 dark:text-slate-300 space-y-1">
                    <div>
                      Рабочее время: <strong>{sc.start_time} — {sc.end_time}</strong>
                    </div>
                    <div>
                      Обед: <strong>{sc.break_duration_minutes} минут</strong>
                    </div>
                    <div>
                      Назначено: <strong>{sc.user_full_name || sc.department_name || 'Для всей компании'}</strong>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* MODAL: EDIT ATTENDANCE RECORD */}
      {editingRecord && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div className="bg-white dark:bg-slate-900 rounded-2xl max-w-md w-full p-6 shadow-2xl border border-slate-200 dark:border-slate-800 space-y-4 animate-in fade-in zoom-in-95">
            <div className="flex items-center gap-2.5 pb-2 border-b border-slate-200 dark:border-slate-800">
              <div className="h-9 w-9 rounded-xl bg-blue-100 dark:bg-blue-950/60 flex items-center justify-center text-blue-600">
                <Edit2 className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-base font-bold text-black dark:text-white">
                  {t.editRecord}
                </h3>
                <p className="text-[11px] text-slate-500 font-medium">
                  {editingRecord.user_full_name} ({editingRecord.record_type === 'check_in' ? 'Пришёл' : 'Ушёл'})
                </p>
              </div>
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-1">
                Скорректированное время и дата
              </label>
              <input
                type="datetime-local"
                value={editTimestamp}
                onChange={(e) => setEditTimestamp(e.target.value)}
                className="w-full text-xs rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 p-2.5 text-black dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-1">
                {t.mandatoryReason} <span className="text-rose-600">*</span>
              </label>
              <textarea
                value={editReason}
                onChange={(e) => setEditReason(e.target.value)}
                placeholder="Например: Забыл отметиться при входе из-за сбоя в сети / Работал удаленно по согласованию"
                className="w-full text-xs rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 p-2.5 text-black dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                rows={3}
              />
            </div>

            <div className="flex justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={() => setEditingRecord(null)}
                className="px-4 py-2 text-xs font-bold rounded-xl border border-slate-300 dark:border-slate-700 text-slate-700 dark:text-slate-300 hover:bg-slate-100"
              >
                {t.cancel}
              </button>
              <button
                type="button"
                onClick={handleSaveEditRecord}
                disabled={savingEdit}
                className="px-4 py-2 text-xs font-bold rounded-xl bg-blue-600 hover:bg-blue-500 text-white shadow-sm"
              >
                Сохранить правку
              </button>
            </div>
          </div>
        </div>
      )}

      {/* MODAL: DAY STATUS (VACATION, SICK LEAVE, BUSINESS TRIP, DAY OFF) */}
      {showDayStatusModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div className="bg-white dark:bg-slate-900 rounded-2xl max-w-md w-full p-6 shadow-2xl border border-slate-200 dark:border-slate-800 space-y-4 animate-in fade-in zoom-in-95">
            <div className="flex items-center gap-2.5 pb-2 border-b border-slate-200 dark:border-slate-800">
              <div className="h-9 w-9 rounded-xl bg-indigo-100 dark:bg-indigo-950/60 flex items-center justify-center text-indigo-600">
                <Calendar className="w-5 h-5" />
              </div>
              <h3 className="text-base font-bold text-black dark:text-white">
                Назначить статус дня
              </h3>
            </div>

            {/* Target Employee selector for manager/director */}
            {isManagerOrDirector && timesheetData?.employees && (
              <div>
                <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-1">
                  Сотрудник
                </label>
                <select
                  value={dayStatusUserId}
                  onChange={(e) => setDayStatusUserId(Number(e.target.value))}
                  className="w-full text-xs rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 p-2.5 text-black dark:text-white"
                >
                  {timesheetData.employees.map((e) => (
                    <option key={e.user_id} value={e.user_id}>
                      {e.full_name} ({e.department_name})
                    </option>
                  ))}
                </select>
              </div>
            )}

            {/* Status Type buttons */}
            <div>
              <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-1.5">
                Тип статуса
              </label>
              <div className="grid grid-cols-2 gap-2">
                {[
                  { id: 'vacation', label: t.vacation },
                  { id: 'sick_leave', label: t.sickLeave },
                  { id: 'business_trip', label: t.businessTrip },
                  { id: 'day_off', label: t.dayOff },
                ].map((s) => (
                  <button
                    key={s.id}
                    type="button"
                    onClick={() => setDayStatusType(s.id as any)}
                    className={`py-2 px-3 text-xs font-bold rounded-xl border text-center transition ${
                      dayStatusType === s.id
                        ? 'bg-blue-600 text-white border-blue-600 shadow-sm'
                        : 'bg-slate-50 dark:bg-slate-800 text-slate-700 dark:text-slate-300 border-slate-300 dark:border-slate-700 hover:bg-slate-100'
                    }`}
                  >
                    {s.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Date Range */}
            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="block text-[11px] font-bold text-slate-700 dark:text-slate-300 mb-1">
                  Дата начала
                </label>
                <input
                  type="date"
                  value={dayStatusStart}
                  onChange={(e) => setDayStatusStart(e.target.value)}
                  className="w-full text-xs rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 p-2 text-black dark:text-white"
                />
              </div>
              <div>
                <label className="block text-[11px] font-bold text-slate-700 dark:text-slate-300 mb-1">
                  Дата окончания
                </label>
                <input
                  type="date"
                  value={dayStatusEnd}
                  onChange={(e) => setDayStatusEnd(e.target.value)}
                  className="w-full text-xs rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 p-2 text-black dark:text-white"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-1">
                Причина / Обоснование
              </label>
              <textarea
                value={dayStatusReason}
                onChange={(e) => setDayStatusReason(e.target.value)}
                placeholder="Приказ №... или лист нетрудоспособности"
                className="w-full text-xs rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 p-2.5 text-black dark:text-white"
                rows={2}
              />
            </div>

            <div className="flex justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={() => setShowDayStatusModal(false)}
                className="px-4 py-2 text-xs font-bold rounded-xl border border-slate-300 dark:border-slate-700 text-slate-700 dark:text-slate-300 hover:bg-slate-100"
              >
                {t.cancel}
              </button>
              <button
                type="button"
                onClick={handleSaveDayStatus}
                className="px-4 py-2 text-xs font-bold rounded-xl bg-blue-600 hover:bg-blue-500 text-white shadow-sm"
              >
                Назначить
              </button>
            </div>
          </div>
        </div>
      )}

      {/* MODAL: ADD/EDIT OFFICE */}
      {showOfficeModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div className="bg-white dark:bg-slate-900 rounded-2xl max-w-md w-full p-6 shadow-2xl border border-slate-200 dark:border-slate-800 space-y-4 animate-in fade-in zoom-in-95">
            <div className="flex items-center gap-2.5 pb-2 border-b border-slate-200 dark:border-slate-800">
              <div className="h-9 w-9 rounded-xl bg-blue-100 dark:bg-blue-950/60 flex items-center justify-center text-blue-600">
                <MapPin className="w-5 h-5" />
              </div>
              <h3 className="text-base font-bold text-black dark:text-white">
                {officeForm.id ? 'Редактировать офис' : 'Новый офис / филиал'}
              </h3>
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-1">
                Название офиса
              </label>
              <input
                type="text"
                value={officeForm.name}
                onChange={(e) => setOfficeForm({ ...officeForm, name: e.target.value })}
                placeholder="Например: Главный офис Бишкек или Филиал Ош"
                className="w-full text-xs rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 p-2.5 text-black dark:text-white"
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-1">
                Адрес
              </label>
              <input
                type="text"
                value={officeForm.address || ''}
                onChange={(e) => setOfficeForm({ ...officeForm, address: e.target.value })}
                placeholder="г. Бишкек, пр. Чуй 120"
                className="w-full text-xs rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 p-2.5 text-black dark:text-white"
              />
            </div>

            {/* GPS coordinates & auto-detect */}
            <div className="space-y-1">
              <div className="flex items-center justify-between">
                <label className="text-xs font-bold text-slate-700 dark:text-slate-300">
                  Координаты офиса (Широта и Долгота)
                </label>
                <button
                  type="button"
                  onClick={handleDetectCoordinates}
                  className="text-[11px] font-bold text-blue-600 hover:underline"
                >
                  Определить текущие
                </button>
              </div>
              <div className="grid grid-cols-2 gap-2">
                <input
                  type="number"
                  step="0.00001"
                  value={officeForm.latitude}
                  onChange={(e) => setOfficeForm({ ...officeForm, latitude: parseFloat(e.target.value) || 0 })}
                  placeholder="Широта (Lat)"
                  className="w-full text-xs rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 p-2 text-black dark:text-white"
                />
                <input
                  type="number"
                  step="0.00001"
                  value={officeForm.longitude}
                  onChange={(e) => setOfficeForm({ ...officeForm, longitude: parseFloat(e.target.value) || 0 })}
                  placeholder="Долгота (Lng)"
                  className="w-full text-xs rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 p-2 text-black dark:text-white"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-1">
                Допустимый радиус отметки (метры)
              </label>
              <input
                type="number"
                value={officeForm.radius_meters}
                onChange={(e) => setOfficeForm({ ...officeForm, radius_meters: parseInt(e.target.value) || 100 })}
                className="w-full text-xs rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 p-2.5 text-black dark:text-white"
              />
            </div>

            {/* IP Verification toggle */}
            <div className="p-3 bg-slate-50 dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 space-y-2">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={officeForm.is_ip_check_enabled}
                  onChange={(e) => setOfficeForm({ ...officeForm, is_ip_check_enabled: e.target.checked })}
                  className="rounded text-blue-600"
                />
                <span className="text-xs font-bold text-black dark:text-white">
                  Включить проверку IP-адреса сети офиса
                </span>
              </label>
              {officeForm.is_ip_check_enabled && (
                <input
                  type="text"
                  value={officeForm.ip_subnet || ''}
                  onChange={(e) => setOfficeForm({ ...officeForm, ip_subnet: e.target.value })}
                  placeholder="Например: 192.168.1.0/24 или 212.42.100.5"
                  className="w-full text-xs rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 p-2 text-black dark:text-white"
                />
              )}
            </div>

            <div className="flex justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={() => setShowOfficeModal(false)}
                className="px-4 py-2 text-xs font-bold rounded-xl border border-slate-300 dark:border-slate-700 text-slate-700 dark:text-slate-300 hover:bg-slate-100"
              >
                {t.cancel}
              </button>
              <button
                type="button"
                onClick={handleSaveOffice}
                className="px-4 py-2 text-xs font-bold rounded-xl bg-blue-600 hover:bg-blue-500 text-white shadow-sm"
              >
                Сохранить
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
