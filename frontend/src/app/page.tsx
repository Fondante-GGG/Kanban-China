'use client';

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { User, BoardSummary, LanguageCode, NotificationItem, WorkspaceTab } from '@/types';
import { api } from '@/lib/api';
import { Navbar } from '@/components/Navbar';
import { BoardView } from '@/components/BoardView';
import { ReportsView } from '@/components/ReportsView';
import { AdminView } from '@/components/AdminView';
import { AttendanceView } from '@/components/AttendanceView';
import { AttendanceWidget } from '@/components/AttendanceWidget';
import { KpiView } from '@/components/KpiView';
import { WarehouseView } from '@/components/WarehouseView';
import { FinanceView } from '@/components/FinanceView';
import { ProcurementView } from '@/components/ProcurementView';
import { LoginModal } from '@/components/LoginModal';
import { EmployeeDirectoryView } from '@/components/EmployeeDirectoryView';
import { ApprovalsView } from '@/components/ApprovalsView';
import { RolesPermissionsView } from '@/components/RolesPermissionsView';
import { EmployeeProfileView } from '@/components/EmployeeProfileView';
import { supplierReturnTranslations } from '@/lib/supplier-returns-i18n';
import { translations, localizeDynamicText } from '@/lib/i18n';
import { Kanban, Layers, UserCheck } from 'lucide-react';

export default function Home() {
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [activeTab, setActiveTab] = useState<WorkspaceTab>('board');
  const [financeReturnId,setFinanceReturnId]=useState<number|undefined>();
  const [financeNavigation,setFinanceNavigation]=useState(0);
  const changeTab=(tab:WorkspaceTab)=>{setFinanceReturnId(undefined);if(tab==='finance')setFinanceNavigation(value=>value+1);setActiveTab(tab);};
  const openSupplierReturn=(returnId:number)=>{if(!currentUser||!(currentUser.role==='general_director'||currentUser.system_permissions?.includes('finance.payable.read')))return;setFinanceReturnId(returnId);setFinanceNavigation(value=>value+1);setActiveTab('finance');setToastNotification(null);};
  const [selectedEmployeeId, setSelectedEmployeeId] = useState<number | null>(null);
  const [boards, setBoards] = useState<BoardSummary[]>([]);
  const [selectedBoardId, setSelectedBoardId] = useState<number | null>(null);
  const [lang, setLang] = useState<LanguageCode>('ru');
  const [darkMode, setDarkMode] = useState<boolean>(false);
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [toastNotification, setToastNotification] = useState<NotificationItem | null>(null);
  const knownNotifIdsRef = useRef<Set<number>>(new Set());
  const [showLoginModal, setShowLoginModal] = useState<boolean>(false);
  const [initialLoading, setInitialLoading] = useState<boolean>(true);

  // Poll only while the app is visible. This prevents background-tab traffic and
  // avoids overlapping requests on a slow connection.
  useEffect(() => {
    if (!currentUser) return;
    let inFlight = false;

    const pollNotifications = async () => {
      if (document.visibilityState !== 'visible' || inFlight) return;
      inFlight = true;
      try {
        const res = await api.getNotifications();
        const incoming: NotificationItem[] = res.notifications || [];

        if (knownNotifIdsRef.current.size > 0) {
          const newest = incoming.find((n) => !n.is_read && !knownNotifIdsRef.current.has(n.id));
          if (newest) {
            setToastNotification(newest);
            window.setTimeout(() => {
              setToastNotification((prev) => (prev?.id === newest.id ? null : prev));
            }, 7000);
          }
        }

        incoming.forEach((n) => knownNotifIdsRef.current.add(n.id));
        setNotifications(incoming);
      } catch {
        // Polling is best-effort; the notification menu can refresh manually.
      } finally {
        inFlight = false;
      }
    };

    void pollNotifications();
    const interval = window.setInterval(() => void pollNotifications(), 30000);
    const onVisibilityChange = () => { if (document.visibilityState === 'visible') void pollNotifications(); };
    document.addEventListener('visibilitychange', onVisibilityChange);

    return () => {
      window.clearInterval(interval);
      document.removeEventListener('visibilitychange', onVisibilityChange);
    };
  }, [currentUser]);

  // Initialize theme & language preferences

  const loadBoardsAndNotifications = useCallback(async (user: User, forceSelectBoardId?: number) => {
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
  }, [setBoards,setNotifications,setSelectedBoardId]);

  const checkAuthSession = useCallback(async () => {
    try {
      const token = api.getToken();
      if (!token) {
        setShowLoginModal(true);
        setInitialLoading(false);
        return;
      }
      const user = await api.getMe();
      setFinanceReturnId(undefined);
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
  }, [loadBoardsAndNotifications,setFinanceReturnId,setCurrentUser,setLang,setShowLoginModal,setInitialLoading]);

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
  }, [checkAuthSession]);

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

  const handleSelectLang = async (newLang: LanguageCode) => {
    setLang(newLang);
    if (typeof window !== 'undefined') {
      localStorage.setItem('kanban_lang', newLang);
    }
    if (currentUser) {
      try {
        const profile = await api.updateInterfaceLanguage(newLang);
        setCurrentUser(profile);
      } catch (error) {
        console.warn('Unable to persist interface language:', error);
      }
    }
  };

  const handleLoginSuccess = async (user: User) => {
    setFinanceReturnId(undefined);
    setCurrentUser(user);
    setShowLoginModal(false);
    if (user.interface_language && ['ru', 'zh-Hans', 'zh-Hant', 'ky'].includes(user.interface_language)) {
      await handleSelectLang(user.interface_language as LanguageCode);
    }
    await loadBoardsAndNotifications(user);
  };

  const handleLogout = () => {
    api.setToken(null);
    setFinanceReturnId(undefined);
    setNotifications([]);
    setToastNotification(null);
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
        setActiveTab={changeTab}
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
        onOpenSupplierReturn={openSupplierReturn}
      />

      {/* Main page attendance widget (Section 4.9: buttons 'Пришёл' & 'Ушёл' for all employees) */}
      {currentUser && (
        <AttendanceWidget
          currentUser={currentUser}
          lang={lang}
          onStatusChange={() => currentUser && loadBoardsAndNotifications(currentUser)}
        />
      )}

      <main className="flex-1 flex flex-col pb-16 lg:pb-0">
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

        {currentUser && activeTab === 'finance' && <FinanceView key={`${currentUser.id}:${financeNavigation}`} currentUser={currentUser} lang={lang} initialReturnId={financeReturnId} />}
        {currentUser && activeTab === 'procurement' && <ProcurementView lang={lang} />}
        {currentUser && activeTab === 'warehouse' && <WarehouseView lang={lang} currentUser={currentUser} />}
        {currentUser && activeTab === 'kpi' && <KpiView lang={lang} currentUser={currentUser} />}

        {currentUser && activeTab === 'hr' && (selectedEmployeeId ? <EmployeeProfileView id={selectedEmployeeId} lang={lang} /> : <EmployeeDirectoryView lang={lang} allowed={currentUser.system_permissions?.includes('hr.employee.read') || currentUser.role === 'general_director'} onOpen={setSelectedEmployeeId} />)}
        {currentUser && activeTab === 'approvals' && <ApprovalsView lang={lang} allowed={currentUser.system_permissions?.includes('approval.read') || currentUser.system_permissions?.includes('approval.act') || currentUser.role === 'general_director'} />}
        {currentUser && activeTab === 'rbac' && <RolesPermissionsView lang={lang} allowed={currentUser.system_permissions?.includes('rbac.manage') || currentUser.role === 'general_director'} />}

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
              {toastNotification.entity_type==='supplier_return'&&toastNotification.entity_id&&(currentUser?.role==='general_director'||currentUser?.system_permissions?.includes('finance.payable.read'))&&<button type="button" className="mt-2 min-h-11 rounded-lg border border-slate-400 px-3 py-2 text-sm font-semibold text-slate-950 dark:border-slate-500 dark:text-slate-100 focus-visible:outline-2 focus-visible:outline-blue-600" onClick={()=>{openSupplierReturn(toastNotification.entity_id!);void api.markNotificationsRead(toastNotification.id).then(refreshNotifications).catch(()=>{});}}>{supplierReturnTranslations[lang].openFinance}</button>}
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
