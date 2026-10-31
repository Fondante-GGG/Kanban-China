'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { AnalyticsData, LanguageCode, User, DepartmentReport, EmployeeReport } from '@/types';
import { 
  translations, 
  localizePersonName, 
  localizeDepartmentName, 
  localizeDynamicText 
} from '@/lib/i18n';
import { api } from '@/lib/api';
import {
  BarChart3,
  CheckCircle2,
  Clock,
  AlertTriangle,
  Bug,
  Building2,
  Users,
  FileSpreadsheet,
  FileText,
  FileDown,
  TrendingUp,
  Search
} from 'lucide-react';

interface ReportsViewProps {
  lang: LanguageCode;
  currentUser: User | null;
}

export const ReportsView: React.FC<ReportsViewProps> = ({ lang, currentUser }) => {
  const t = translations[lang] || translations.ru;
  const [period, setPeriod] = useState<'week' | 'month' | 'quarter'>('month');
  const [data, setData] = useState<AnalyticsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [exportingFormat, setExportingFormat] = useState<string | null>(null);
  const [searchEmployee, setSearchEmployee] = useState('');

  const loadReports = useCallback(async () => {
    try {
      setLoading(true);
      const res = await api.getAnalytics(period);
      setData(res);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, [period]);

  useEffect(() => {
    loadReports();
  }, [loadReports]);

  const handleExport = async (format: 'xlsx' | 'docx' | 'pdf') => {
    try {
      setExportingFormat(format);
      await api.downloadExport(format, period);
    } catch (err: any) {
      alert(err.message || 'Ошибка экспорта отчёта');
    } finally {
      setExportingFormat(null);
    }
  };

  if (!currentUser?.role || currentUser.role !== 'general_director') {
    return (
      <div className="flex-1 flex flex-col items-center justify-center min-h-[60vh] p-6 text-center">
        <div className="w-14 h-14 rounded-2xl bg-amber-50 dark:bg-amber-950/50 text-amber-600 flex items-center justify-center mb-4 border border-amber-200">
          <AlertTriangle className="w-8 h-8" />
        </div>
        <h3 className="text-lg font-bold text-slate-900 dark:text-white">Доступ ограничен</h3>
        <p className="text-sm text-slate-500 max-w-md mt-1">
          Раздел отчётов и аналитики доступен исключительно Генеральному директору компании.
        </p>
      </div>
    );
  }

  const filteredEmployees = data?.employees.filter((emp) =>
    emp.full_name.toLowerCase().includes(searchEmployee.toLowerCase()) ||
    emp.department_name.toLowerCase().includes(searchEmployee.toLowerCase()) ||
    emp.email.toLowerCase().includes(searchEmployee.toLowerCase())
  ) || [];

  return (
    <div className="flex-1 p-4 sm:p-8 max-w-7xl mx-auto w-full space-y-8 animate-in fade-in duration-300">
      {/* Header & Controls */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-6 border-b border-slate-200 dark:border-slate-800">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="h-10 w-10 rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-600 flex items-center justify-center text-white shadow-md shadow-blue-500/20">
              <BarChart3 className="w-5 h-5" />
            </div>
            <div>
              <h1 className="text-xl sm:text-2xl font-black text-black dark:text-white tracking-tight">
                {t.reports}
              </h1>
              <p className="text-xs text-slate-800 dark:text-slate-300 font-semibold mt-0.5">
                Сводные показатели эффективности сотрудников и подразделений компании
              </p>
            </div>
          </div>
        </div>

        {/* Toolbar: Period selector & Export buttons */}
        <div className="flex flex-wrap items-center gap-2.5">
          {/* Period buttons */}
          <div className="flex items-center p-1 rounded-xl bg-slate-200 dark:bg-slate-800 border border-slate-300 dark:border-slate-700">
            <button
              onClick={() => setPeriod('week')}
              className={`px-3 py-1.5 rounded-lg text-xs font-bold transition ${
                period === 'week'
                  ? 'bg-white dark:bg-slate-900 text-black dark:text-white shadow-sm'
                  : 'text-black dark:text-white hover:opacity-80'
              }`}
            >
              {t.week}
            </button>
            <button
              onClick={() => setPeriod('month')}
              className={`px-3 py-1.5 rounded-lg text-xs font-bold transition ${
                period === 'month'
                  ? 'bg-white dark:bg-slate-900 text-black dark:text-white shadow-sm'
                  : 'text-black dark:text-white hover:opacity-80'
              }`}
            >
              {t.month}
            </button>
            <button
              onClick={() => setPeriod('quarter')}
              className={`px-3 py-1.5 rounded-lg text-xs font-bold transition ${
                period === 'quarter'
                  ? 'bg-white dark:bg-slate-900 text-black dark:text-white shadow-sm'
                  : 'text-black dark:text-white hover:opacity-80'
              }`}
            >
              {t.quarter}
            </button>
          </div>

          {/* Export Buttons */}
          <div className="flex items-center gap-1.5">
            <button
              onClick={() => handleExport('xlsx')}
              disabled={exportingFormat !== null}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-emerald-400 dark:border-emerald-800 bg-emerald-100 dark:bg-emerald-950 text-black dark:text-white hover:bg-emerald-200 text-xs font-bold transition shadow-sm disabled:opacity-50"
              title={t.exportExcel}
            >
              <FileSpreadsheet className="w-3.5 h-3.5 text-black dark:text-white" />
              <span>Excel</span>
            </button>

            <button
              onClick={() => handleExport('docx')}
              disabled={exportingFormat !== null}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-blue-400 dark:border-blue-800 bg-blue-100 dark:bg-blue-950 text-black dark:text-white hover:bg-blue-200 text-xs font-bold transition shadow-sm disabled:opacity-50"
              title={t.exportWord}
            >
              <FileText className="w-3.5 h-3.5 text-black dark:text-white" />
              <span>Word</span>
            </button>

            <button
              onClick={() => handleExport('pdf')}
              disabled={exportingFormat !== null}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-rose-400 dark:border-rose-800 bg-rose-100 dark:bg-rose-950 text-black dark:text-white hover:bg-rose-200 text-xs font-bold transition shadow-sm disabled:opacity-50"
              title={t.exportPdf}
            >
              <FileDown className="w-3.5 h-3.5 text-black dark:text-white" />
              <span>PDF</span>
            </button>
          </div>
        </div>
      </div>

      {loading && !data ? (
        <div className="py-20 flex flex-col items-center justify-center gap-3">
          <div className="w-10 h-10 rounded-full border-3 border-blue-500 border-t-transparent animate-spin" />
          <p className="text-xs text-black dark:text-slate-300 font-bold">Формирование отчётов...</p>
        </div>
      ) : data ? (
        <>
          {/* Executive KPI Cards */}
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 sm:gap-4">
            {/* Total Tasks */}
            <div className="p-4 rounded-2xl bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-800 shadow-sm relative overflow-hidden">
              <div className="flex items-center justify-between text-black dark:text-white mb-2">
                <span className="text-xs font-extrabold uppercase tracking-wider">{t.total}</span>
                <BarChart3 className="w-4 h-4 text-blue-600" />
              </div>
              <div className="text-2xl font-black text-black dark:text-white">
                {data.summary.total_tasks}
              </div>
              <div className="mt-1 text-[11px] text-slate-800 dark:text-slate-300 font-bold">За период: {data.period}</div>
            </div>

            {/* Completed */}
            <div className="p-4 rounded-2xl bg-white dark:bg-slate-900 border border-emerald-300 dark:border-emerald-900/60 shadow-sm relative overflow-hidden bg-gradient-to-b from-emerald-50/40 to-transparent">
              <div className="flex items-center justify-between text-emerald-800 dark:text-emerald-400 mb-2">
                <span className="text-xs font-extrabold uppercase tracking-wider">{t.completed}</span>
                <CheckCircle2 className="w-4 h-4" />
              </div>
              <div className="text-2xl font-black text-emerald-700 dark:text-emerald-400">
                {data.summary.completed_tasks}
              </div>
              <div className="mt-1 text-[11px] text-emerald-900 dark:text-emerald-300 font-bold">
                Успешно закрыто
              </div>
            </div>

            {/* In Progress */}
            <div className="p-4 rounded-2xl bg-white dark:bg-slate-900 border border-blue-300 dark:border-blue-900/60 shadow-sm relative overflow-hidden bg-gradient-to-b from-blue-50/40 to-transparent">
              <div className="flex items-center justify-between text-blue-800 dark:text-blue-400 mb-2">
                <span className="text-xs font-extrabold uppercase tracking-wider">{t.inProgress}</span>
                <Clock className="w-4 h-4" />
              </div>
              <div className="text-2xl font-black text-blue-700 dark:text-blue-400">
                {data.summary.in_progress_tasks}
              </div>
              <div className="mt-1 text-[11px] text-blue-900 dark:text-blue-300 font-bold">
                В активной работе
              </div>
            </div>

            {/* Overdue */}
            <div className="p-4 rounded-2xl bg-white dark:bg-slate-900 border border-rose-300 dark:border-rose-900/60 shadow-sm relative overflow-hidden bg-gradient-to-b from-rose-50/40 to-transparent">
              <div className="flex items-center justify-between text-rose-800 dark:text-rose-400 mb-2">
                <span className="text-xs font-extrabold uppercase tracking-wider">{t.overdue}</span>
                <AlertTriangle className="w-4 h-4" />
              </div>
              <div className="text-2xl font-black text-rose-700 dark:text-rose-400">
                {data.summary.overdue_tasks}
              </div>
              <div className="mt-1 text-[11px] text-rose-900 dark:text-rose-300 font-bold">
                Требуют внимания
              </div>
            </div>

            {/* Bugs */}
            <div className="p-4 rounded-2xl bg-white dark:bg-slate-900 border border-amber-300 dark:border-amber-900/60 shadow-sm relative overflow-hidden bg-gradient-to-b from-amber-50/40 to-transparent">
              <div className="flex items-center justify-between text-amber-800 dark:text-amber-400 mb-2">
                <span className="text-xs font-extrabold uppercase tracking-wider">{t.bugs}</span>
                <Bug className="w-4 h-4" />
              </div>
              <div className="text-2xl font-black text-amber-700 dark:text-amber-400">
                {data.summary.bug_tasks}
              </div>
              <div className="mt-1 text-[11px] text-amber-900 dark:text-amber-300 font-bold">
                Дефекты в работе
              </div>
            </div>

            {/* Success Rate */}
            <div className="p-4 rounded-2xl bg-white dark:bg-slate-900 border border-indigo-300 dark:border-indigo-900/60 shadow-sm relative overflow-hidden bg-gradient-to-b from-indigo-50/40 to-transparent">
              <div className="flex items-center justify-between text-indigo-800 dark:text-indigo-400 mb-2">
                <span className="text-xs font-extrabold uppercase tracking-wider">{t.successRate}</span>
                <TrendingUp className="w-4 h-4" />
              </div>
              <div className="text-2xl font-black text-indigo-700 dark:text-indigo-400">
                {data.summary.completion_rate}%
              </div>
              <div className="mt-1 text-[11px] text-indigo-900 dark:text-indigo-300 font-bold">
                Конверсия в результат
              </div>
            </div>
          </div>

          {/* Department Breakdown Cards */}
          <div className="space-y-4">
            <div className="flex items-center gap-2">
              <Building2 className="w-5 h-5 text-blue-700 dark:text-blue-400" />
              <h2 className="text-base sm:text-lg font-black text-black dark:text-white">
                {t.departmentReport}
              </h2>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {data.departments.map((dept: DepartmentReport) => (
                <div
                  key={dept.id}
                  className="p-5 rounded-2xl bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-800 shadow-sm space-y-4 hover:shadow-md transition"
                >
                  <div className="flex items-start justify-between">
                    <div>
                      <h3 className="font-extrabold text-sm text-black dark:text-white">{localizeDepartmentName(dept.name, lang)}</h3>
                      <p className="text-xs font-bold text-slate-800 dark:text-slate-300 mt-0.5">{dept.total} {localizeDynamicText('задач всего', lang)}</p>
                    </div>
                    <span className="px-2.5 py-1 rounded-full text-xs font-black bg-blue-100 dark:bg-blue-950/60 text-blue-900 dark:text-blue-300 border border-blue-300 dark:border-blue-800">
                      {dept.completion_rate}%
                    </span>
                  </div>

                  {/* Progress bar */}
                  <div className="space-y-1">
                    <div className="h-2.5 w-full bg-slate-200 dark:bg-slate-800 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-gradient-to-r from-blue-600 to-indigo-600 rounded-full transition-all"
                        style={{ width: `${dept.completion_rate}%` }}
                      />
                    </div>
                  </div>

                  {/* Metrics Row */}
                  <div className="grid grid-cols-3 gap-2 pt-2 border-t border-slate-200 dark:border-slate-800 text-center text-xs">
                    <div>
                      <span className="block text-black dark:text-slate-300 text-[10px] uppercase font-bold">Готово</span>
                      <span className="font-black text-emerald-700 dark:text-emerald-400 text-sm">{dept.completed}</span>
                    </div>
                    <div>
                      <span className="block text-black dark:text-slate-300 text-[10px] uppercase font-bold">В работе</span>
                      <span className="font-black text-blue-700 dark:text-blue-400 text-sm">{dept.in_progress}</span>
                    </div>
                    <div>
                      <span className="block text-black dark:text-slate-300 text-[10px] uppercase font-bold">Просрочено</span>
                      <span className="font-black text-rose-700 dark:text-rose-400 text-sm">{dept.overdue}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Employee Performance Table */}
          <div className="space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div className="flex items-center gap-2">
                <Users className="w-5 h-5 text-blue-700 dark:text-blue-400" />
                <h2 className="text-base sm:text-lg font-black text-black dark:text-white">
                  {t.employeeReport}
                </h2>
              </div>

              {/* Employee Search */}
              <div className="relative">
                <Search className="w-3.5 h-3.5 text-black dark:text-white absolute left-3 top-1/2 -translate-y-1/2" />
                <input
                  type="text"
                  value={searchEmployee}
                  onChange={(e) => setSearchEmployee(e.target.value)}
                  placeholder="Поиск по сотруднику или отделу..."
                  className="pl-8 pr-3 py-1.5 text-xs font-semibold rounded-xl border border-slate-400 dark:border-slate-700 bg-white dark:bg-slate-800 text-black dark:text-white placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500/20 w-64"
                />
              </div>
            </div>

            <div className="overflow-hidden rounded-2xl border border-slate-300 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm">
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-100 dark:bg-slate-850 text-black dark:text-white uppercase tracking-wider font-extrabold border-b border-slate-300 dark:border-slate-800">
                    <tr>
                      <th className="py-3.5 px-4">{t.fullName}</th>
                      <th className="py-3.5 px-4">{t.department}</th>
                      <th className="py-3.5 px-3 text-center">Назначено</th>
                      <th className="py-3.5 px-3 text-center">{t.completed}</th>
                      <th className="py-3.5 px-3 text-center">{t.inProgress}</th>
                      <th className="py-3.5 px-3 text-center">{t.overdue}</th>
                      <th className="py-3.5 px-3 text-center">{t.avgCompletionHours}</th>
                      <th className="py-3.5 px-4 text-center">{t.successRate}</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-200 dark:divide-slate-800/80">
                    {filteredEmployees.length === 0 ? (
                      <tr>
                        <td colSpan={8} className="py-8 text-center text-xs text-black dark:text-slate-300 font-bold">
                          Сотрудники не найдены
                        </td>
                      </tr>
                    ) : (
                      filteredEmployees.map((emp: EmployeeReport) => (
                        <tr key={emp.id} className="hover:bg-slate-50 dark:hover:bg-slate-850/50 transition">
                          <td className="py-3 px-4">
                            <div className="flex items-center gap-2.5">
                              <div className="h-7 w-7 rounded-full bg-slate-900 text-white font-bold text-xs flex items-center justify-center">
                                {emp.full_name.charAt(0)}
                              </div>
                              <div>
                                <div className="font-extrabold text-black dark:text-white">{localizePersonName(emp.full_name, lang)}</div>
                                <div className="text-[11px] text-slate-800 dark:text-slate-300 font-medium">{emp.email}</div>
                              </div>
                            </div>
                          </td>
                          <td className="py-3 px-4 font-bold text-black dark:text-slate-200">
                            {localizeDepartmentName(emp.department_name, lang)}
                          </td>
                          <td className="py-3 px-3 text-center font-extrabold text-black dark:text-slate-200">
                            {emp.assigned_count}
                          </td>
                          <td className="py-3 px-3 text-center font-extrabold text-emerald-700 dark:text-emerald-400">
                            {emp.completed_count}
                          </td>
                          <td className="py-3 px-3 text-center font-extrabold text-blue-700 dark:text-blue-400">
                            {emp.in_progress_count}
                          </td>
                          <td className="py-3 px-3 text-center font-extrabold text-rose-700 dark:text-rose-400">
                            {emp.overdue_count}
                          </td>
                          <td className="py-3 px-3 text-center font-bold text-black dark:text-slate-200">
                            {emp.avg_completion_hours > 0 ? `${emp.avg_completion_hours} ч` : '—'}
                          </td>
                          <td className="py-3 px-4 text-center">
                            <span
                              className={`inline-block px-2.5 py-1 rounded-full text-xs font-black border ${
                                emp.completion_rate >= 80
                                  ? 'bg-emerald-100 text-black border-emerald-300 dark:bg-emerald-950/60 dark:text-white'
                                  : emp.completion_rate >= 50
                                  ? 'bg-blue-100 text-black border-blue-300 dark:bg-blue-950/60 dark:text-white'
                                  : 'bg-slate-200 text-black border-slate-300 dark:bg-slate-800 dark:text-white'
                              }`}
                            >
                              {emp.completion_rate}%
                            </span>
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </>
      ) : null}
    </div>
  );
};
