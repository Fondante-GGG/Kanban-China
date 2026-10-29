'use client';

import React, { useState, useEffect } from 'react';
import { User, BoardSummary, LanguageCode, NotificationItem } from '@/types';
import { api } from '@/lib/api';
import { Navbar } from '@/components/Navbar';
import { BoardView } from '@/components/BoardView';
import { ReportsView } from '@/components/ReportsView';
import { AdminView } from '@/components/AdminView';
import { AttendanceView } from '@/components/AttendanceView';
import { AttendanceWidget } from '@/components/AttendanceWidget';
import { LoginModal } from '@/components/LoginModal';
import { translations } from '@/lib/i18n';
import { Kanban, Layers } from 'lucide-react';

export default function Home() {
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [activeTab, setActiveTab] = useState<'board' | 'reports' | 'admin' | 'attendance'>('board');
  const [boards, setBoards] = useState<BoardSummary[]>([]);
  const [selectedBoardId, setSelectedBoardId] = useState<number | null>(null);
  const [lang, setLang] = useState<LanguageCode>('ru');
  const [darkMode, setDarkMode] = useState<boolean>(false);
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [showLoginModal, setShowLoginModal] = useState<boolean>(false);
  const [initialLoading, setInitialLoading] = useState<boolean>(true);

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
    </div>
  );
}
