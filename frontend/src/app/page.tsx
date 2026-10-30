'use client';

import React, { useState, useEffect, useRef } from 'react';
import { User, BoardSummary, LanguageCode, NotificationItem } from '@/types';
import { api } from '@/lib/api';
import { Navbar } from '@/components/Navbar';
import { BoardView } from '@/components/BoardView';
import { ReportsView } from '@/components/ReportsView';
import { AdminView } from '@/components/AdminView';
import { AttendanceView } from '@/components/AttendanceView';
import { AttendanceWidget } from '@/components/AttendanceWidget';
import { FinanceView } from '@/components/FinanceView';
import { LoginModal } from '@/components/LoginModal';
import { translations, localizeDynamicText } from '@/lib/i18n';
import { Kanban, Layers, UserCheck } from 'lucide-react';

export default function Home() {
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [activeTab, setActiveTab] = useState<'board' | 'reports' | 'admin' | 'attendance' | 'finance'>('board');
  const [boards, setBoards] = useState<BoardSummary[]>([]);
  const [selectedBoardId, setSelectedBoardId] = useState<number | null>(null);
  const [lang, setLang] = useState<LanguageCode>('ru');
  const [darkMode, setDarkMode] = useState<boolean>(false);
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [toastNotification, setToastNotification] = useState<NotificationItem | null>(null);
  const knownNotifIdsRef = useRef<Set<number>>(new Set());
  const [showLoginModal, setShowLoginModal] = useState<boolean>(false);
  const [initialLoading, setInitialLoading] = useState<boolean>(true);

  // Periodic notifications polling (every 6 seconds) for real-time alerts
  useEffect(() => {
    if (!currentUser) return;

    const interval = setInterval(async () => {
      try {
        const res = await api.getNotifications();
        const incoming: NotificationItem[] = res.notifications || [];

        // Detect new unread notification for toast alert
        if (knownNotifIdsRef.current.size > 0) {
          const newest = incoming.find((n) => !n.is_read && !knownNotifIdsRef.current.has(n.id));
          if (newest) {
            setToastNotification(newest);
            // Auto dismiss toast after 7 seconds
            setTimeout(() => {
              setToastNotification((prev) => (prev?.id === newest.id ? null : prev));
            }, 7000);
          }
        }

        // Update known IDs
        incoming.forEach((n) => knownNotifIdsRef.current.add(n.id));
        setNotifications(incoming);
      } catch (err) {
        // Silent poll error
      }
    }, 6000);

    return () => clearInterval(interval);
  }, [currentUser]);

  // Initialize theme & language preferences
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const savedTheme = localStorage.getItem('kanban_theme');
      const isDark = savedTheme === 'dark';
      setDarkMode(isDark);
      document.documentElement.classList.toggle('dark', isDark);

      const savedLang = localStorage.getItem('kanban_lang') as LanguageCode;
      if (savedLang && ['ru', 'zh-Hans', 'zh-Hant', 'ky'].includes(savedLang)) {
        setLang(savedLang);
      }
    }
    checkAuthSession();
  }, []);

  const checkAuthSession = async () => {
    try {
      const token = api.getToken();
      if (!token) {
        setShowLoginModal(true);
        setInitialLoading(false);
        return;
      }
      const user = await api.getMe();
      setCurrentUser(user);
      if (user.interface_language && ['ru', 'zh-Hans', 'zh-Hant', 'ky'].includes(user.interface_language)) {
        setLang(user.interface_language as LanguageCode);
      }
      await loadBoardsAndNotifications(user);
    } catch (err) {
      console.warn('Auth check failed, prompting login:', err);
      setShowLoginModal(true);
    } finally {
      setInitialLoading(false);
    }
  };

  const loadBoardsAndNotifications = async (user: User, forceSelectBoardId?: number) => {
    try {
      const [boardsRes, notifsRes] = await Promise.all([
        api.getBoards(),
        api.getNotifications(),
      ]);

      const availableBoards = boardsRes.boards;
      setBoards(availableBoards);
      setNotifications(notifsRes.notifications);
      (notifsRes.notifications || []).forEach((n: NotificationItem) => knownNotifIdsRef.current.add(n.id));

      // Select active board
      if (forceSelectBoardId && availableBoards.some((b: any) => b.id === forceSelectBoardId)) {
        setSelectedBoardId(forceSelectBoardId);
        if (typeof window !== 'undefined') {
          localStorage.setItem('kanban_last_board', forceSelectBoardId.toString());
        }
      } else if (availableBoards.length > 0) {
        const lastSelected = localStorage.getItem('kanban_last_board');
        const match = availableBoards.find((b: any) => b.id.toString() === lastSelected);
        if (match) {
          setSelectedBoardId(match.id);
        } else if (user.assigned_board_id && availableBoards.some((b: any) => b.id === user.assigned_board_id)) {
          setSelectedBoardId(user.assigned_board_id);
        } else {
          setSelectedBoardId(availableBoards[0].id);
        }
      } else {
        setSelectedBoardId(null);
      }
    } catch (err) {
      console.error('Error loading boards or notifications:', err);
    }
  };

  const handleSelectBoard = (boardId: number) => {
    setSelectedBoardId(boardId);
    if (typeof window !== 'undefined') {
      localStorage.setItem('kanban_last_board', boardId.toString());
    }
  };

  const handleToggleDarkMode = () => {
    const nextDark = !darkMode;
    setDarkMode(nextDark);
    if (typeof window !== 'undefined') {
      localStorage.setItem('kanban_theme', nextDark ? 'dark' : 'light');
      document.documentElement.classList.toggle('dark', nextDark);
    }
  };

  const handleSelectLang = (newLang: LanguageCode) => {
    setLang(newLang);
    if (typeof window !== 'undefined') {
      localStorage.setItem('kanban_lang', newLang);
    }
  };

  const handleLoginSuccess = async (user: User) => {
    setCurrentUser(user);
    setShowLoginModal(false);
    if (user.interface_language && ['ru', 'zh-Hans', 'zh-Hant', 'ky'].includes(user.interface_language)) {
      handleSelectLang(user.interface_language as LanguageCode);
    }
    await loadBoardsAndNotifications(user);
  };

  const handleLogout = () => {
    api.setToken(null);
    setCurrentUser(null);
    setBoards([]);
    setSelectedBoardId(null);
    setShowLoginModal(true);
    setActiveTab('board');
  };

  const refreshNotifications = async () => {
    try {
      const res = await api.getNotifications();
      setNotifications(res.notifications);
    } catch (err) {
      console.error(err);
    }
  };

  if (initialLoading) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center bg-slate-900 text-white gap-4">
        <div className="h-12 w-12 rounded-2xl bg-gradient-to-tr from-blue-600 via-indigo-600 to-violet-600 flex items-center justify-center shadow-lg shadow-blue-500/30 animate-pulse">
          <Kanban className="w-6 h-6 text-white" />
        </div>
        <div className="text-sm font-semibold text-slate-300">
          Инициализация Yrys Kanban...
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex flex-col bg-slate-50 dark:bg-slate-950 text-black dark:text-white transition-colors">
      <Navbar
        currentUser={currentUser}
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        boards={boards}
        selectedBoardId={selectedBoardId}
        onSelectBoard={handleSelectBoard}
        lang={lang}
        onSelectLang={handleSelectLang}
        darkMode={darkMode}
        onToggleDarkMode={handleToggleDarkMode}
        onLogout={handleLogout}
        notifications={notifications}
        onRefreshNotifications={refreshNotifications}
      />

      {/* Main page attendance widget (Section 4.9: buttons 'Пришёл' & 'Ушёл' for all employees) */}
      {currentUser && (
        <AttendanceWidget
          currentUser={currentUser}
          lang={lang}
          onStatusChange={() => currentUser && loadBoardsAndNotifications(currentUser)}
        />
      )}

      <main className="flex-1 flex flex-col">
        {currentUser && selectedBoardId && activeTab === 'board' && (
          <BoardView
            boardId={selectedBoardId}
            lang={lang}
            currentUser={currentUser}
            onRefreshBoardsList={() => currentUser && loadBoardsAndNotifications(currentUser)}
          />
        )}

        {currentUser && (!selectedBoardId || boards.length === 0) && activeTab === 'board' && (
          <div className="flex-1 flex flex-col items-center justify-center min-h-[60vh] p-8 text-center">
            <div className="h-16 w-16 rounded-2xl bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 flex items-center justify-center mb-4 border border-slate-300 dark:border-slate-700">
              <Layers className="w-8 h-8" />
            </div>
            <h3 className="text-lg font-bold text-black dark:text-white">
              {translations[lang]?.noBoardsFound || 'Нет доступных досок'}
            </h3>
            <p className="text-xs text-slate-800 dark:text-slate-300 font-medium max-w-sm mt-1">
              Администратор ещё не привязал вас к канбан-доске или доски ещё не были созданы.
            </p>
          </div>
        )}

        {currentUser && activeTab === 'reports' && (
          <ReportsView lang={lang} currentUser={currentUser} />
        )}

        {currentUser && activeTab === 'attendance' && (
          <AttendanceView lang={lang} currentUser={currentUser} />
        )}

        {currentUser && activeTab === 'finance' && <FinanceView currentUser={currentUser} lang={lang} />}

        {currentUser && activeTab === 'admin' && (
          <AdminView
            lang={lang}
            currentUser={currentUser}
            onRefreshBoards={(newBoardId?: number) => currentUser && loadBoardsAndNotifications(currentUser, newBoardId)}
          />
        )}
      </main>

      {/* Login Modal */}
      {showLoginModal && (
        <LoginModal
          onSuccess={handleLoginSuccess}
          lang={lang}
        />
      )}

      {/* Real-time Notification Toast Alert */}
      {toastNotification && (
        <div className="fixed bottom-5 right-5 z-50 max-w-sm w-full bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 shadow-2xl rounded-2xl p-4 animate-in slide-in-from-bottom-5 fade-in duration-300">
          <div className="flex items-start gap-3">
            <div className="h-9 w-9 rounded-xl bg-emerald-100 dark:bg-emerald-950/60 text-emerald-600 flex items-center justify-center flex-shrink-0">
              <UserCheck className="w-5 h-5" />
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center justify-between gap-1">
                <span className="font-extrabold text-xs text-black dark:text-white truncate">
                  {localizeDynamicText(toastNotification.title, lang)}
                </span>
                <button
                  onClick={() => setToastNotification(null)}
                  className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 text-xs font-bold p-0.5"
                >
                  ✕
                </button>
              </div>
              <p className="mt-1 text-xs text-slate-800 dark:text-slate-200 leading-relaxed font-medium">
                {localizeDynamicText(toastNotification.message, lang)}
              </p>
              {toastNotification.created_at && (
                <div className="mt-1 text-[10px] text-slate-500 font-semibold">
                  {new Date(toastNotification.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
