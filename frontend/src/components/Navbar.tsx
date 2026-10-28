'use client';

import React, { useState } from 'react';
import { User, LanguageCode, BoardSummary, NotificationItem } from '@/types';
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
  Kanban, 
  BarChart3, 
  ShieldCheck, 
  Sun, 
  Moon, 
  Globe2, 
  Bell, 
  LogOut, 
  ChevronDown, 
  CheckCheck,
  Building2,
  Layers
} from 'lucide-react';

interface NavbarProps {
  currentUser: User | null;
  activeTab: 'board' | 'reports' | 'admin';
  setActiveTab: (tab: 'board' | 'reports' | 'admin') => void;
  boards: BoardSummary[];
  selectedBoardId: number | null;
  onSelectBoard: (boardId: number) => void;
  lang: LanguageCode;
  onSelectLang: (lang: LanguageCode) => void;
  darkMode: boolean;
  onToggleDarkMode: () => void;
  onLogout: () => void;
  notifications: NotificationItem[];
  onRefreshNotifications: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  currentUser,
  activeTab,
  setActiveTab,
  boards,
  selectedBoardId,
  onSelectBoard,
  lang,
  onSelectLang,
  darkMode,
  onToggleDarkMode,
  onLogout,
  notifications,
  onRefreshNotifications,
}) => {
  const t = translations[lang] || translations.ru;
  const [showLangMenu, setShowLangMenu] = useState(false);
  const [showUserMenu, setShowUserMenu] = useState(false);
  const [showNotifMenu, setShowNotifMenu] = useState(false);

  const unreadCount = notifications.filter((n) => !n.is_read).length;

  const handleMarkAllRead = async () => {
    try {
      await api.markNotificationsRead();
      onRefreshNotifications();
    } catch (e) {
      console.error(e);
    }
  };

  const getRoleBadge = (role?: string) => {
    switch (role) {
      case 'general_director':
        return { label: t.roleDirector, color: 'bg-amber-100 dark:bg-amber-950/60 text-black dark:text-white border-amber-300 dark:border-amber-800' };
      case 'manager':
        return { label: t.roleManager, color: 'bg-blue-100 dark:bg-blue-950/60 text-black dark:text-white border-blue-300 dark:border-blue-800' };
      case 'employee':
      default:
        return { label: t.roleEmployee, color: 'bg-emerald-100 dark:bg-emerald-950/60 text-black dark:text-white border-emerald-300 dark:border-emerald-800' };
    }
  };

  const roleInfo = getRoleBadge(currentUser?.role);

  return (
    <header className="sticky top-0 z-40 w-full border-b border-slate-200 dark:border-slate-800 bg-white/95 dark:bg-slate-900/95 backdrop-blur transition-colors">
      <div className="flex h-16 items-center justify-between px-4 sm:px-6 max-w-full">
        {/* Brand & Board Selector */}
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2.5">
            <div className="h-9 w-9 rounded-xl bg-gradient-to-tr from-blue-600 via-indigo-600 to-violet-600 flex items-center justify-center shadow-md shadow-blue-500/20 text-white font-bold">
              <Kanban className="w-5 h-5" />
            </div>
            <div className="hidden sm:block">
              <span className="font-extrabold text-lg tracking-tight text-black dark:text-white">
                {t.appName}
              </span>
            </div>
          </div>

          {/* Boards dropdown */}
          {boards.length > 0 && (
            <div className="relative">
              <select
                value={selectedBoardId || ''}
                onChange={(e) => onSelectBoard(Number(e.target.value))}
                aria-label={t.board}
                className="appearance-none pl-3 pr-8 py-1.5 text-xs sm:text-sm font-bold rounded-lg border border-slate-400 dark:border-slate-700 bg-white dark:bg-slate-800 text-black dark:text-white hover:border-slate-600 dark:hover:border-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500/20 transition-all cursor-pointer max-w-[200px] sm:max-w-[320px] truncate"
              >
                {boards.map((b) => {
                  const locDept = localizeDepartmentName(b.department_name, lang);
                  const locTitle = localizeBoardTitle(b.title, lang);
                  let label = locTitle;
                  if (locDept) {
                    if (
                      b.title.trim().toLowerCase() === (b.department_name || '').trim().toLowerCase() ||
                      b.title.trim().toLowerCase() === `доска: ${(b.department_name || '').trim().toLowerCase()}`
                    ) {
                      label = locDept;
                    } else {
                      label = `${locDept} — ${locTitle}`;
                    }
                  }
                  return (
                    <option key={b.id} value={b.id} className="text-black bg-white dark:bg-slate-800 dark:text-white font-medium">
                      {label}
                    </option>
                  );
                })}
              </select>
              <ChevronDown className="w-4 h-4 text-black dark:text-slate-300 absolute right-2.5 top-1/2 -translate-y-1/2 pointer-events-none" />
            </div>
          )}
        </div>

        {/* Navigation Tabs */}
        {currentUser && (
          <nav className="hidden lg:flex items-center gap-1 p-1 bg-slate-200 dark:bg-slate-800/70 rounded-xl border border-slate-300 dark:border-slate-700/60">
            <button
              onClick={() => setActiveTab('board')}
              className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs sm:text-sm font-bold transition-all ${
                activeTab === 'board'
                  ? 'bg-white dark:bg-slate-900 text-black dark:text-white shadow-sm'
                  : 'text-black dark:text-white hover:opacity-80'
              }`}
            >
              <Layers className="w-4 h-4" />
              {t.board}
            </button>

            {currentUser.role === 'general_director' && (
              <>
                <button
                  onClick={() => setActiveTab('reports')}
                  className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs sm:text-sm font-bold transition-all ${
                    activeTab === 'reports'
                      ? 'bg-white dark:bg-slate-900 text-black dark:text-white shadow-sm'
                      : 'text-black dark:text-white hover:opacity-80'
                  }`}
                >
                  <BarChart3 className="w-4 h-4" />
                  {t.reports}
                </button>

                <button
                  onClick={() => setActiveTab('admin')}
                  className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs sm:text-sm font-bold transition-all ${
                    activeTab === 'admin'
                      ? 'bg-white dark:bg-slate-900 text-black dark:text-white shadow-sm'
                      : 'text-black dark:text-white hover:opacity-80'
                  }`}
                >
                  <ShieldCheck className="w-4 h-4" />
                  {t.admin}
                </button>
              </>
            )}
          </nav>
        )}

        {/* Action Controls & Utilities */}
        <div className="flex items-center gap-2">
          {/* Language Switcher */}
          <div className="relative">
            <button
              onClick={() => {
                setShowLangMenu(!showLangMenu);
                setShowNotifMenu(false);
                setShowUserMenu(false);
              }}
              className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-bold rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-black dark:text-white hover:bg-slate-50 dark:hover:bg-slate-750 transition"
              title={t.language}
            >
              <Globe2 className="w-3.5 h-3.5 text-blue-600" />
              <span className="uppercase font-bold">{lang === 'zh-Hans' ? '简中' : lang === 'zh-Hant' ? '繁中' : lang}</span>
              <ChevronDown className="w-3 h-3 opacity-80" />
            </button>

            {showLangMenu && (
              <div className="absolute right-0 mt-2 w-44 rounded-xl bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-800 shadow-xl py-1 z-50 animate-in fade-in slide-in-from-top-2 duration-150">
                <button
                  onClick={() => {
                    onSelectLang('ru');
                    setShowLangMenu(false);
                  }}
                  className={`w-full text-left px-3.5 py-2 text-xs font-semibold flex items-center justify-between hover:bg-slate-100 dark:hover:bg-slate-800 ${
                    lang === 'ru' ? 'text-blue-700 font-bold dark:text-blue-400' : 'text-black dark:text-slate-200'
                  }`}
                >
                  <span>🇷🇺 Русский (RU)</span>
                  {lang === 'ru' && <span className="text-blue-600">✓</span>}
                </button>
                <button
                  onClick={() => {
                    onSelectLang('zh-Hans');
                    setShowLangMenu(false);
                  }}
                  className={`w-full text-left px-3.5 py-2 text-xs font-semibold flex items-center justify-between hover:bg-slate-100 dark:hover:bg-slate-800 ${
                    lang === 'zh-Hans' ? 'text-blue-700 font-bold dark:text-blue-400' : 'text-black dark:text-slate-200'
                  }`}
                >
                  <span>🇨🇳 简体中文 (ZH)</span>
                  {lang === 'zh-Hans' && <span className="text-blue-600">✓</span>}
                </button>
                <button
                  onClick={() => {
                    onSelectLang('zh-Hant');
                    setShowLangMenu(false);
                  }}
                  className={`w-full text-left px-3.5 py-2 text-xs font-semibold flex items-center justify-between hover:bg-slate-100 dark:hover:bg-slate-800 ${
                    lang === 'zh-Hant' ? 'text-blue-700 font-bold dark:text-blue-400' : 'text-black dark:text-slate-200'
                  }`}
                >
                  <span>🇭🇰 繁體中文 (ZH-TW)</span>
                  {lang === 'zh-Hant' && <span className="text-blue-600">✓</span>}
                </button>
                <button
                  onClick={() => {
                    onSelectLang('ky');
                    setShowLangMenu(false);
                  }}
                  className={`w-full text-left px-3.5 py-2 text-xs font-semibold flex items-center justify-between hover:bg-slate-100 dark:hover:bg-slate-800 ${
                    lang === 'ky' ? 'text-blue-700 font-bold dark:text-blue-400' : 'text-black dark:text-slate-200'
                  }`}
                >
                  <span>🇰🇬 Кыргызча (KY)</span>
                  {lang === 'ky' && <span className="text-blue-600">✓</span>}
                </button>
              </div>
            )}
          </div>

          {/* Theme Toggle */}
          <button
            onClick={onToggleDarkMode}
            className="p-2 rounded-lg text-black hover:text-blue-600 dark:text-slate-200 dark:hover:text-white border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 transition"
            title={t.theme}
          >
            {darkMode ? <Sun className="w-4 h-4 text-amber-400" /> : <Moon className="w-4 h-4 text-black" />}
          </button>

          {/* Notifications Center */}
          <div className="relative">
            <button
              onClick={() => {
                setShowNotifMenu(!showNotifMenu);
                setShowLangMenu(false);
                setShowUserMenu(false);
              }}
              className="relative p-2 rounded-lg text-black hover:text-blue-600 dark:text-slate-200 dark:hover:text-white border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 transition"
              title={t.notifications}
            >
              <Bell className="w-4 h-4 text-black dark:text-white" />
              {unreadCount > 0 && (
                <span className="absolute -top-1 -right-1 h-4 min-w-[16px] px-1 bg-rose-600 text-white text-[10px] font-bold rounded-full flex items-center justify-center animate-pulse">
                  {unreadCount}
                </span>
              )}
            </button>

            {showNotifMenu && (
              <div className="absolute right-0 mt-2 w-80 sm:w-96 rounded-2xl bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-800 shadow-2xl py-3 z-50 animate-in fade-in slide-in-from-top-2 duration-150">
                <div className="flex items-center justify-between px-4 pb-2.5 border-b border-slate-200 dark:border-slate-800">
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-sm text-black dark:text-white">{t.notifications}</span>
                    {unreadCount > 0 && (
                      <span className="px-2 py-0.5 rounded-full text-[11px] font-bold bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-300">
                        {unreadCount}
                      </span>
                    )}
                  </div>
                  {unreadCount > 0 && (
                    <button
                      onClick={handleMarkAllRead}
                      className="text-xs text-blue-700 dark:text-blue-400 font-bold hover:underline flex items-center gap-1"
                    >
                      <CheckCheck className="w-3.5 h-3.5" />
                      {t.markAllRead}
                    </button>
                  )}
                </div>

                <div className="max-h-80 overflow-y-auto divide-y divide-slate-100 dark:divide-slate-800/60">
                  {notifications.length === 0 ? (
                    <div className="py-8 text-center text-xs text-slate-800 dark:text-slate-300 font-medium">
                      {t.noNotifications}
                    </div>
                  ) : (
                    notifications.map((notif) => (
                      <div
                        key={notif.id}
                        className={`p-3.5 transition-colors ${
                          !notif.is_read ? 'bg-blue-50/70 dark:bg-blue-950/20' : 'hover:bg-slate-50 dark:hover:bg-slate-850'
                        }`}
                      >
                        <div className="flex items-start justify-between gap-2">
                          <span className="font-bold text-xs text-black dark:text-white">{localizeDynamicText(notif.title, lang)}</span>
                          {!notif.is_read && <span className="h-2 w-2 rounded-full bg-blue-600 mt-1 flex-shrink-0" />}
                        </div>
                        <p className="mt-1 text-xs text-slate-900 dark:text-slate-200 font-medium leading-relaxed">{localizeDynamicText(notif.message, lang)}</p>
                        {notif.created_at && (
                          <div className="mt-1.5 text-[10px] text-slate-700 dark:text-slate-400 font-medium">
                            {new Date(notif.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                          </div>
                        )}
                      </div>
                    ))
                  )}
                </div>
              </div>
            )}
          </div>

          {/* User Profile & Menu */}
          {currentUser && (
            <div className="relative">
              <button
                onClick={() => {
                  setShowUserMenu(!showUserMenu);
                  setShowLangMenu(false);
                  setShowNotifMenu(false);
                }}
                className="flex items-center gap-2 p-1 pl-2 rounded-xl border border-slate-300 dark:border-slate-800 hover:bg-slate-100 dark:hover:bg-slate-800 transition"
              >
                <div className="hidden sm:flex flex-col items-end leading-tight text-right">
                  <span className="font-bold text-xs text-black dark:text-white max-w-[140px] truncate">
                    {localizePersonName(currentUser.full_name, lang)}
                  </span>
                  <span className={`text-[10px] font-bold px-1.5 py-0.2 rounded border ${roleInfo.color}`}>
                    {roleInfo.label}
                  </span>
                </div>
                <div className="h-8 w-8 rounded-lg bg-gradient-to-tr from-slate-800 to-black text-white font-bold text-xs flex items-center justify-center shadow">
                  {currentUser.full_name.charAt(0)}
                </div>
              </button>

              {showUserMenu && (
                <div className="absolute right-0 mt-2 w-64 rounded-xl bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-800 shadow-xl py-2 z-50 animate-in fade-in slide-in-from-top-2 duration-150">
                  <div className="px-4 py-2 border-b border-slate-200 dark:border-slate-800">
                    <p className="font-bold text-xs text-black dark:text-white">{localizePersonName(currentUser.full_name, lang)}</p>
                    <p className="text-[11px] text-slate-800 dark:text-slate-300 font-medium truncate">{currentUser.email}</p>
                    {currentUser.department_name && (
                      <p className="text-[11px] text-slate-800 dark:text-slate-300 font-semibold flex items-center gap-1 mt-1">
                        <Building2 className="w-3 h-3 text-blue-600" />
                        {localizeDepartmentName(currentUser.department_name, lang)}
                      </p>
                    )}
                  </div>

                  <div className="py-1">
                    <button
                      onClick={() => {
                        onLogout();
                        setShowUserMenu(false);
                      }}
                      className="w-full text-left px-4 py-2 text-xs text-rose-700 dark:text-rose-400 hover:bg-rose-50 dark:hover:bg-rose-950/30 flex items-center gap-2 font-bold transition"
                    >
                      <LogOut className="w-3.5 h-3.5" />
                      {t.logout}
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </header>
  );
};
