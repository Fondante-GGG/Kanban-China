'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { BoardDetail, Column, Card, LanguageCode, User, PriorityType } from '@/types';
import { 
  translations, 
  getLocalizedText, 
  localizePersonName, 
  localizeDepartmentName, 
  localizeBoardTitle, 
  localizeRole, 
  localizeDynamicText 
} from '@/lib/i18n';
import { api } from '@/lib/api';
import { CardDetailModal } from '@/components/CardDetailModal';
import { useBoardWebSocket, WebSocketEvent } from '@/lib/useBoardWebSocket';
import {
  Plus,
  Search,
  Filter,
  MoreVertical,
  Calendar,
  Clock,
  Paperclip,
  MessageSquare,
  CheckSquare,
  Palette,
  Edit2,
  Trash2,
  AlertCircle,
  Building2,
  Users,
  ChevronLeft,
  ChevronRight,
  GripVertical
} from 'lucide-react';

interface BoardViewProps {
  boardId: number;
  lang: LanguageCode;
  currentUser: User | null;
  onRefreshBoardsList: () => void;
}

const THEMES = [
  { id: 'gradient-blue', name: 'Океан (Синий)', class: 'bg-gradient-to-br from-blue-700 via-indigo-800 to-slate-950' },
  { id: 'gradient-purple', name: 'Неон (Пурпур)', class: 'bg-gradient-to-br from-purple-700 via-violet-900 to-slate-950' },
  { id: 'gradient-emerald', name: 'Изумруд (Зелёный)', class: 'bg-gradient-to-br from-emerald-700 via-teal-900 to-slate-950' },
  { id: 'gradient-sunset', name: 'Закат (Янтарь)', class: 'bg-gradient-to-br from-rose-700 via-amber-800 to-slate-950' },
  { id: 'slate-minimal', name: 'Минимализм (Серый)', class: 'bg-slate-100 dark:bg-slate-950' },
  { id: 'obsidian', name: 'Обсидиан (Тёмный)', class: 'bg-zinc-950' },
];

export const BoardView: React.FC<BoardViewProps> = ({
  boardId,
  lang,
  currentUser,
  onRefreshBoardsList,
}) => {
  const t = translations[lang] || translations.ru;
  const [board, setBoard] = useState<BoardDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Search & Filter state
  const [search, setSearch] = useState('');
  const [selectedPriority, setSelectedPriority] = useState<string>('');
  const [selectedAssigneeId, setSelectedAssigneeId] = useState<number | undefined>(undefined);

  // Modals & Popovers
  const [selectedCardId, setSelectedCardId] = useState<number | null>(null);
  const [showThemePicker, setShowThemePicker] = useState(false);

  // Create Column Modal
  const [showAddColumnModal, setShowAddColumnModal] = useState(false);
  const [newColumnTitle, setNewColumnTitle] = useState('');

  // Rename Column
  const [editingColumnId, setEditingColumnId] = useState<number | null>(null);
  const [editColumnTitle, setEditColumnTitle] = useState('');

  // Quick Add Card Modal
  const [addingCardColumnId, setAddingCardColumnId] = useState<number | null>(null);
  const [newCardTitle, setNewCardTitle] = useState('');
  const [newCardDesc, setNewCardDesc] = useState('');
  const [newCardPriority, setNewCardPriority] = useState<PriorityType>('medium');
  const [newCardDueDate, setNewCardDueDate] = useState('');
  const [newCardAssigneeIds, setNewCardAssigneeIds] = useState<number[]>([]);

  // Drag and Drop State (Cards & Columns)
  const [draggedCardId, setDraggedCardId] = useState<number | null>(null);
  const [dragOverColId, setDragOverColId] = useState<number | null>(null);
  const [draggedColumnId, setDraggedColumnId] = useState<number | null>(null);
  const [dragOverColHeaderId, setDragOverColHeaderId] = useState<number | null>(null);
  const [newColumnPosition, setNewColumnPosition] = useState<string>('end');

  useEffect(() => {
    loadBoard();
  }, [boardId, search, selectedPriority, selectedAssigneeId]);

  const loadBoardSilently = useCallback(async () => {
    try {
      const data = await api.getBoardDetail(boardId, {
        search: search || undefined,
        priority: selectedPriority || undefined,
        assignee_id: selectedAssigneeId || undefined,
      });
      setBoard(data);
    } catch (err) {
      console.warn('Silent board sync failed:', err);
    }
  }, [boardId, search, selectedPriority, selectedAssigneeId]);

  const loadBoard = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await api.getBoardDetail(boardId, {
        search: search || undefined,
        priority: selectedPriority || undefined,
        assignee_id: selectedAssigneeId || undefined,
      });
      setBoard(data);
    } catch (err: any) {
      setError(err.message || 'Ошибка загрузки доски');
    } finally {
      setLoading(false);
    }
  };

  const handleWebSocketEvent = useCallback((event: WebSocketEvent) => {
    if (event.is_self) {
      // Ignore self messages as we already applied them optimistically
      return;
    }

    if (event.type === 'card_moved' && event.card_id && event.target_column_id) {
      setBoard((prev) => {
        if (!prev) return prev;
        let cardToMove: Card | null = null;
        for (const col of prev.columns) {
          const c = col.cards.find((card) => card.id === event.card_id);
          if (c) {
            cardToMove = c;
            break;
          }
        }
        if (!cardToMove) {
          loadBoardSilently();
          return prev;
        }

        const targetColId = event.target_column_id!;
        const updatedCard: Card = {
          ...cardToMove,
          column_id: targetColId,
          order: event.target_order ?? 0,
        };

        const nextColumns = prev.columns.map((col) => {
          if (col.id === targetColId && col.cards.some((c) => c.id === event.card_id)) {
            return col;
          }
          const filtered = col.cards.filter((c) => c.id !== event.card_id);
          if (col.id === targetColId) {
            const nextCards = [...filtered, updatedCard];
            return {
              ...col,
              cards: nextCards,
              cards_count: nextCards.length,
            };
          }
          return {
            ...col,
            cards: filtered,
            cards_count: filtered.length,
          };
        });

        return {
          ...prev,
          columns: nextColumns,
        };
      });
      return;
    }

    // For other updates (card_created, card_updated, card_deleted, checklist_*, columns)
    loadBoardSilently();
  }, [loadBoardSilently]);

  const { sendEvent } = useBoardWebSocket(boardId, handleWebSocketEvent);

  const currentTheme = THEMES.find((th) => th.id === board?.background_theme) || THEMES[0];

  // Theme changer
  const handleChangeTheme = async (themeId: string) => {
    try {
      await api.updateBoard(boardId, { background_theme: themeId });
      setShowThemePicker(false);
      loadBoard();
      onRefreshBoardsList();
    } catch (err: any) {
      alert(err.message || 'Ошибка обновления темы');
    }
  };

  // Add Column
  const handleCreateColumn = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newColumnTitle.trim() || !board) return;
    const titleToCreate = newColumnTitle.trim();
    const pos = newColumnPosition;

    try {
      const createdCol = await api.createColumn({
        board_id: boardId,
        title: titleToCreate,
        language: lang === 'zh-Hans' || lang === 'zh-Hant' ? 'zh' : lang,
      });

      setNewColumnTitle('');
      setShowAddColumnModal(false);
      setNewColumnPosition('end');

      // If user selected a custom position
      if (pos === 'start') {
        const reordered = [createdCol, ...board.columns];
        const columnOrders = reordered.map((c: any, idx: number) => ({ id: c.id, order: idx }));
        await api.reorderColumns(boardId, columnOrders);
      } else if (pos.startsWith('before_')) {
        const targetId = Number(pos.replace('before_', ''));
        const targetIdx = board.columns.findIndex((c) => c.id === targetId);
        if (targetIdx !== -1) {
          const reordered = [...board.columns];
          reordered.splice(targetIdx, 0, createdCol);
          const columnOrders = reordered.map((c: any, idx: number) => ({ id: c.id, order: idx }));
          await api.reorderColumns(boardId, columnOrders);
        }
      }

      loadBoard();
    } catch (err: any) {
      alert(err.message || 'Ошибка создания раздела');
    }
  };

  // Rename Column
  const handleRenameColumn = async (columnId: number) => {
    if (!editColumnTitle.trim()) return;
    try {
      await api.updateColumn(columnId, {
        title: editColumnTitle.trim(),
        language: lang === 'zh-Hans' || lang === 'zh-Hant' ? 'zh' : lang,
      });
      setEditingColumnId(null);
      setEditColumnTitle('');
      loadBoard();
    } catch (err: any) {
      alert(err.message || 'Ошибка переименования раздела');
    }
  };

  // Delete Column
  const handleDeleteColumn = async (columnId: number) => {
    if (!confirm(t.confirmDelete)) return;
    try {
      await api.deleteColumn(columnId);
      loadBoard();
    } catch (err: any) {
      alert(err.message || 'Ошибка удаления раздела');
    }
  };

  // Add Card
  const handleCreateCard = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!addingCardColumnId || !newCardTitle.trim()) return;
    try {
      await api.createCard({
        column_id: addingCardColumnId,
        title: newCardTitle.trim(),
        description: newCardDesc.trim(),
        priority: newCardPriority,
        due_date: newCardDueDate || undefined,
        assignee_ids: newCardAssigneeIds,
        language: lang === 'zh-Hans' || lang === 'zh-Hant' ? 'zh' : lang,
      });
      setAddingCardColumnId(null);
      setNewCardTitle('');
      setNewCardDesc('');
      setNewCardPriority('medium');
      setNewCardDueDate('');
      setNewCardAssigneeIds([]);
      loadBoard();
    } catch (err: any) {
      alert(err.message || 'Ошибка создания карточки');
    }
  };

  // HTML5 Drag and drop handlers
  const handleDragStart = (cardId: number, e: React.DragEvent) => {
    if (!board?.permissions?.can_move_cards) return;
    setDraggedCardId(cardId);
    e.dataTransfer.setData('text/plain', cardId.toString());
    e.dataTransfer.effectAllowed = 'move';
  };

  const handleDragOver = (colId: number, e: React.DragEvent) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
    if (draggedColumnId) {
      if (dragOverColHeaderId !== colId) {
        setDragOverColHeaderId(colId);
      }
    } else {
      if (dragOverColId !== colId) {
        setDragOverColId(colId);
      }
    }
  };

  // Move column left or right by 1 step
  const handleMoveColumn = async (columnId: number, direction: 'left' | 'right') => {
    if (!board || !board.permissions?.can_manage_columns) return;
    const currentIndex = board.columns.findIndex((c) => c.id === columnId);
    if (currentIndex === -1) return;

    const targetIndex = direction === 'left' ? currentIndex - 1 : currentIndex + 1;
    if (targetIndex < 0 || targetIndex >= board.columns.length) return;

    const previousBoard = board;
    const reordered = [...board.columns];
    const [movedCol] = reordered.splice(currentIndex, 1);
    reordered.splice(targetIndex, 0, movedCol);

    const nextColumns = reordered.map((c, idx) => ({
      ...c,
      order: idx,
    }));

    const columnOrders = reordered.map((c, idx) => ({
      id: c.id,
      order: idx,
    }));

    // 1. Optimistic instant reorder (0ms latency)
    setBoard({
      ...board,
      columns: nextColumns,
    });

    // 2. Broadcast over WebSocket
    sendEvent({
      type: 'columns_reordered',
      board_id: boardId,
    });

    // 3. Persist to API
    try {
      await api.reorderColumns(boardId, columnOrders);
    } catch (err: any) {
      setBoard(previousBoard);
      alert(err.message || 'Ошибка изменения порядка разделов');
    }
  };

  // Drag and drop handler for columns
  const handleColumnDrop = async (targetColId: number) => {
    const sourceColId = draggedColumnId;
    setDraggedColumnId(null);
    setDragOverColId(null);
    setDragOverColHeaderId(null);

    if (!sourceColId || sourceColId === targetColId || !board) return;

    const sourceIdx = board.columns.findIndex((c) => c.id === sourceColId);
    const targetIdx = board.columns.findIndex((c) => c.id === targetColId);
    if (sourceIdx === -1 || targetIdx === -1) return;

    const previousBoard = board;
    const reordered = [...board.columns];
    const [movedCol] = reordered.splice(sourceIdx, 1);
    reordered.splice(targetIdx, 0, movedCol);

    const nextColumns = reordered.map((c, idx) => ({
      ...c,
      order: idx,
    }));

    const columnOrders = reordered.map((c, idx) => ({
      id: c.id,
      order: idx,
    }));

    // 1. Optimistic update
    setBoard({
      ...board,
      columns: nextColumns,
    });

    // 2. Broadcast via WebSocket
    sendEvent({
      type: 'columns_reordered',
      board_id: boardId,
    });

    // 3. Persist to API
    try {
      await api.reorderColumns(boardId, columnOrders);
    } catch (err: any) {
      setBoard(previousBoard);
      alert(err.message || 'Ошибка перемещения раздела');
    }
  };

  // Optimistic Move Handler (0ms instant UI update)
  const handleMoveCardDirectly = async (cardId: number, targetColId: number) => {
    if (!board) return;

    let sourceColId: number | null = null;
    let cardToMove: Card | null = null;

    for (const col of board.columns) {
      const found = col.cards.find((c) => c.id === cardId);
      if (found) {
        sourceColId = col.id;
        cardToMove = found;
        break;
      }
    }

    if (!cardToMove || sourceColId === null || sourceColId === targetColId) return;

    const previousBoard = board;
    const targetCol = board.columns.find((c) => c.id === targetColId);
    const newOrder = targetCol?.cards.length || 0;

    const updatedCard: Card = {
      ...cardToMove,
      column_id: targetColId,
      order: newOrder,
    };

    const newColumns = board.columns.map((col) => {
      if (col.id === sourceColId) {
        const remaining = col.cards.filter((c) => c.id !== cardId);
        return {
          ...col,
          cards: remaining,
          cards_count: remaining.length,
        };
      }
      if (col.id === targetColId) {
        const appended = [...col.cards, updatedCard];
        return {
          ...col,
          cards: appended,
          cards_count: appended.length,
        };
      }
      return col;
    });

    // 1. Immediately apply to local state
    setBoard({
      ...board,
      columns: newColumns,
    });

    // 2. Broadcast over WebSocket to all other users immediately
    sendEvent({
      type: 'card_moved',
      card_id: cardId,
      source_column_id: sourceColId,
      target_column_id: targetColId,
      target_order: newOrder,
    });

    // 3. Persist to API
    try {
      await api.moveCard(cardId, targetColId, newOrder);
    } catch (err: any) {
      // Revert if rejected
      setBoard(previousBoard);
      alert(err.message || 'Ошибка перемещения карточки');
    }
  };

  const handleDrop = async (targetColId: number, e: React.DragEvent) => {
    e.preventDefault();
    setDragOverColId(null);
    setDragOverColHeaderId(null);

    // If moving a column/section:
    if (draggedColumnId) {
      handleColumnDrop(targetColId);
      return;
    }

    const cardId = draggedCardId;
    if (!cardId || !board) return;

    let sourceColId: number | null = null;
    let cardToMove: Card | null = null;

    for (const col of board.columns) {
      const found = col.cards.find((c) => c.id === cardId);
      if (found) {
        sourceColId = col.id;
        cardToMove = found;
        break;
      }
    }

    if (!cardToMove || sourceColId === null) {
      setDraggedCardId(null);
      return;
    }

    if (sourceColId === targetColId) {
      setDraggedCardId(null);
      return;
    }

    // 1. Optimistic Update (instant 0ms card transfer)
    const previousBoard = board;
    const targetCol = board.columns.find((c) => c.id === targetColId);
    const newOrder = targetCol?.cards.length || 0;

    const updatedCard: Card = {
      ...cardToMove,
      column_id: targetColId,
      order: newOrder,
    };

    const newColumns = board.columns.map((col) => {
      if (col.id === sourceColId) {
        const remaining = col.cards.filter((c) => c.id !== cardId);
        return {
          ...col,
          cards: remaining,
          cards_count: remaining.length,
        };
      }
      if (col.id === targetColId) {
        const appended = [...col.cards, updatedCard];
        return {
          ...col,
          cards: appended,
          cards_count: appended.length,
        };
      }
      return col;
    });

    setBoard({
      ...board,
      columns: newColumns,
    });
    setDraggedCardId(null);

    // 2. Broadcast via WebSocket
    sendEvent({
      type: 'card_moved',
      card_id: cardId,
      source_column_id: sourceColId,
      target_column_id: targetColId,
      target_order: newOrder,
    });

    // 3. Persist to server
    try {
      await api.moveCard(cardId, targetColId, newOrder);
    } catch (err: any) {
      setBoard(previousBoard);
      alert(err.message || 'Ошибка перемещения карточки');
    }
  };

  const getPriorityStyle = (p: string) => {
    switch (p) {
      case 'urgent':
        return {
          pill: 'bg-rose-100 dark:bg-rose-950/60 text-black dark:text-white border-rose-300 dark:border-rose-800',
          dot: 'bg-rose-600',
          label: t.priorityUrgent,
        };
      case 'high':
        return {
          pill: 'bg-amber-100 dark:bg-amber-950/60 text-black dark:text-white border-amber-300 dark:border-amber-800',
          dot: 'bg-amber-600',
          label: t.priorityHigh,
        };
      case 'low':
        return {
          pill: 'bg-slate-200 dark:bg-slate-800 text-black dark:text-white border-slate-300 dark:border-slate-700',
          dot: 'bg-slate-500',
          label: t.priorityLow,
        };
      case 'medium':
      default:
        return {
          pill: 'bg-blue-100 dark:bg-blue-950/60 text-black dark:text-white border-blue-300 dark:border-blue-800',
          dot: 'bg-blue-600',
          label: t.priorityMedium,
        };
    }
  };

  if (loading && !board) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center min-h-[60vh] gap-3">
        <div className="w-10 h-10 rounded-full border-3 border-blue-500 border-t-transparent animate-spin" />
        <p className="text-sm text-slate-500 font-medium">Загрузка канбан-доски...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center min-h-[60vh] p-6 text-center">
        <div className="w-14 h-14 rounded-2xl bg-rose-50 dark:bg-rose-950/60 text-rose-600 dark:text-rose-400 flex items-center justify-center mb-4 border border-rose-200 dark:border-rose-800 shadow-sm">
          <AlertCircle className="w-8 h-8" />
        </div>
        <h3 className="text-lg font-bold text-slate-900 dark:text-white">Доступ ограничен (403)</h3>
        <p className="text-sm text-slate-500 max-w-md mt-1">{error}</p>
      </div>
    );
  }

  if (!board) return null;

  return (
    <div className={`flex-1 flex flex-col min-h-[calc(100vh-4rem)] transition-colors duration-500 ${currentTheme.class}`}>
      {/* Board Subheader Toolbar */}
      <div className="w-full px-4 sm:px-6 py-3.5 backdrop-blur-md bg-white/70 dark:bg-slate-900/80 border-b border-slate-200/60 dark:border-slate-800/80 flex flex-wrap items-center justify-between gap-3 shadow-sm">
        {/* Left: Title, Department & Members */}
        <div className="flex items-center gap-3 flex-wrap">
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-base sm:text-lg font-black text-black dark:text-white tracking-tight">
                {localizeBoardTitle(board.title, lang)}
              </h1>
              {board.department_name && (
                <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold bg-blue-100 dark:bg-blue-950/60 text-black dark:text-white border border-blue-300 dark:border-blue-800">
                  <Building2 className="w-3 h-3 text-blue-700 dark:text-blue-400" />
                  {localizeDepartmentName(board.department_name, lang)}
                </span>
              )}
            </div>
          </div>

          {/* Members Avatars Stack */}
          {board.members.length > 0 && (
            <div className="flex items-center -space-x-1.5 overflow-hidden pl-2 border-l border-slate-300 dark:border-slate-700">
              {board.members.map((m) => (
                <div
                  key={m.user_id}
                  title={`${localizePersonName(m.full_name, lang)} (${m.board_role === 'manager' ? t.roleManager : t.roleEmployee})`}
                  className="h-7 w-7 rounded-full bg-slate-900 text-white font-bold text-[10px] flex items-center justify-center ring-2 ring-white dark:ring-slate-900 shadow-sm cursor-help"
                >
                  {m.full_name.charAt(0)}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Right: Search, Filter, Theme, Add Column */}
        <div className="flex items-center gap-2 flex-wrap">
          {/* Search Box */}
          <div className="relative">
            <Search className="w-3.5 h-3.5 text-black dark:text-white absolute left-2.5 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder={t.searchPlaceholder}
              className="pl-8 pr-3 py-1.5 text-xs font-semibold rounded-lg border border-slate-400 dark:border-slate-700 bg-white dark:bg-slate-800 text-black dark:text-white placeholder:text-slate-600 dark:placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500/20 w-36 sm:w-56 transition"
            />
          </div>

          {/* Priority Filter */}
          <select
            value={selectedPriority}
            onChange={(e) => setSelectedPriority(e.target.value)}
            className="text-xs font-bold py-1.5 px-2.5 rounded-lg border border-slate-400 dark:border-slate-700 bg-white dark:bg-slate-800 text-black dark:text-white focus:outline-none cursor-pointer"
          >
            <option value="">{t.allPriorities}</option>
            <option value="urgent">{t.priorityUrgent}</option>
            <option value="high">{t.priorityHigh}</option>
            <option value="medium">{t.priorityMedium}</option>
            <option value="low">{t.priorityLow}</option>
          </select>

          {/* Theme Palette Button */}
          <div className="relative">
            <button
              onClick={() => setShowThemePicker(!showThemePicker)}
              className="p-1.5 rounded-lg border border-slate-400 dark:border-slate-700 bg-white dark:bg-slate-800 text-black dark:text-white hover:bg-slate-100 transition"
              title={t.changeBackground}
            >
              <Palette className="w-4 h-4 text-indigo-700 dark:text-indigo-400" />
            </button>

            {showThemePicker && (
              <div className="absolute right-0 mt-2 w-52 rounded-xl bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-800 shadow-xl p-2 z-50 animate-in fade-in slide-in-from-top-2 duration-150">
                <div className="text-[11px] font-bold text-black dark:text-white uppercase tracking-wider px-2 py-1">
                  {t.changeBackground}
                </div>
                <div className="space-y-1 mt-1">
                  {THEMES.map((th) => (
                    <button
                      key={th.id}
                      onClick={() => handleChangeTheme(th.id)}
                      className="w-full text-left px-2.5 py-1.5 rounded-lg text-xs font-bold flex items-center gap-2 hover:bg-slate-100 dark:hover:bg-slate-800 text-black dark:text-white transition"
                    >
                      <span className={`w-3.5 h-3.5 rounded-full ${th.class} ring-1 ring-slate-400 dark:ring-slate-700`} />
                      <span>{th.name}</span>
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Add Column Button (Director & Manager) */}
          {board.permissions.can_manage_columns && (
            <button
              onClick={() => setShowAddColumnModal(true)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold shadow-sm transition"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>{t.addColumn}</span>
            </button>
          )}
        </div>
      </div>

      {/* Kanban Board Container (Horizontal Scroll) */}
      <div className="flex-1 p-4 sm:p-6 overflow-x-auto flex items-start gap-4 custom-scrollbar">
        {board.columns.map((column: Column, colIndex: number) => {
          const isCardDragOver = dragOverColId === column.id && !draggedColumnId;
          const isColDragOver = dragOverColHeaderId === column.id && !!draggedColumnId;
          const isBeingDragged = draggedColumnId === column.id;
          const colTitle = getLocalizedText(column, 'title', lang, false);

          return (
            <div
              key={column.id}
              onDragOver={(e) => handleDragOver(column.id, e)}
              onDrop={(e) => handleDrop(column.id, e)}
              className={`w-72 sm:w-80 flex-shrink-0 flex flex-col rounded-2xl max-h-[calc(100vh-10rem)] border backdrop-blur-md transition-all duration-200 shadow-lg ${
                isColDragOver
                  ? 'bg-blue-100/90 dark:bg-blue-900/40 border-blue-600 ring-4 ring-blue-500/30 scale-[1.01]'
                  : isCardDragOver
                  ? 'bg-blue-50/90 dark:bg-blue-950/40 border-blue-400 ring-2 ring-blue-500/20'
                  : 'bg-white/85 dark:bg-slate-900/85 border-white/40 dark:border-slate-800/80'
              } ${isBeingDragged ? 'opacity-40' : ''}`}
            >
              {/* Column Header (Draggable for reordering) */}
              <div
                draggable={board.permissions.can_manage_columns}
                onDragStart={(e) => {
                  if (!board.permissions.can_manage_columns) return;
                  setDraggedColumnId(column.id);
                  e.dataTransfer.setData('text/column-id', column.id.toString());
                  e.dataTransfer.effectAllowed = 'move';
                }}
                onDragEnd={() => {
                  setDraggedColumnId(null);
                  setDragOverColHeaderId(null);
                }}
                onDragOver={(e) => {
                  if (draggedColumnId && draggedColumnId !== column.id) {
                    e.preventDefault();
                    setDragOverColHeaderId(column.id);
                  }
                }}
                className={`p-3 pb-2.5 flex items-center justify-between border-b border-slate-300 dark:border-slate-800/60 select-none ${
                  board.permissions.can_manage_columns ? 'cursor-grab active:cursor-grabbing' : ''
                }`}
              >
                <div className="flex items-center gap-1.5 min-w-0 flex-1">
                  {board.permissions.can_manage_columns && (
                    <div
                      className="text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 transition p-0.5"
                      title="Перетащите раздел мышью"
                    >
                      <GripVertical className="w-4 h-4" />
                    </div>
                  )}

                  {editingColumnId === column.id ? (
                    <div className="flex items-center gap-1 flex-1">
                      <input
                        type="text"
                        value={editColumnTitle}
                        onChange={(e) => setEditColumnTitle(e.target.value)}
                        className="text-xs p-1 rounded border border-blue-500 bg-white dark:bg-slate-800 text-black dark:text-white font-bold w-full"
                        autoFocus
                      />
                      <button
                        onClick={() => handleRenameColumn(column.id)}
                        className="text-[10px] bg-blue-600 text-white px-1.5 py-1 rounded font-bold"
                      >
                        ✓
                      </button>
                    </div>
                  ) : (
                    <h3 className="font-extrabold text-xs sm:text-sm text-black dark:text-white truncate">
                      {colTitle}
                    </h3>
                  )}
                  <span className="px-2 py-0.5 rounded-full text-[11px] font-extrabold bg-slate-200 dark:bg-slate-800 text-black dark:text-white flex-shrink-0">
                    {column.cards_count}
                  </span>
                </div>

                {/* Column options (for Director & Manager) */}
                {board.permissions.can_manage_columns && (
                  <div className="flex items-center gap-0.5 flex-shrink-0">
                    {/* Move Left */}
                    <button
                      type="button"
                      disabled={colIndex === 0}
                      onClick={(e) => {
                        e.stopPropagation();
                        handleMoveColumn(column.id, 'left');
                      }}
                      className="p-1 rounded text-black hover:text-blue-600 disabled:opacity-20 disabled:hover:text-black dark:text-slate-300 dark:hover:text-white dark:disabled:hover:text-slate-300 transition"
                      title="Сдвинуть раздел влево"
                    >
                      <ChevronLeft className="w-4 h-4" />
                    </button>

                    {/* Move Right */}
                    <button
                      type="button"
                      disabled={colIndex === board.columns.length - 1}
                      onClick={(e) => {
                        e.stopPropagation();
                        handleMoveColumn(column.id, 'right');
                      }}
                      className="p-1 rounded text-black hover:text-blue-600 disabled:opacity-20 disabled:hover:text-black dark:text-slate-300 dark:hover:text-white dark:disabled:hover:text-slate-300 transition"
                      title="Сдвинуть раздел вправо"
                    >
                      <ChevronRight className="w-4 h-4" />
                    </button>

                    {/* Rename */}
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        setEditingColumnId(column.id);
                        setEditColumnTitle(colTitle);
                      }}
                      className="p-1 rounded text-black hover:text-blue-600 dark:text-slate-300 transition"
                      title={t.renameColumn}
                    >
                      <Edit2 className="w-3.5 h-3.5" />
                    </button>

                    {/* Delete */}
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleDeleteColumn(column.id);
                      }}
                      className="p-1 rounded text-black hover:text-rose-600 dark:text-slate-300 transition"
                      title={t.deleteColumn}
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                )}
              </div>

              {/* Quick Add Card Button at top */}
              {board.permissions.can_manage_cards && (
                <div className="px-3 pt-2">
                  <button
                    onClick={() => {
                      setAddingCardColumnId(column.id);
                      setNewCardTitle('');
                    }}
                    className="w-full py-1.5 px-2.5 rounded-xl border border-dashed border-slate-400 dark:border-slate-700 text-black dark:text-slate-200 hover:border-blue-600 hover:text-blue-600 dark:hover:text-blue-400 text-xs font-bold flex items-center justify-center gap-1.5 transition bg-white dark:bg-slate-850/50 shadow-sm"
                  >
                    <Plus className="w-3.5 h-3.5 text-black dark:text-slate-200" />
                    <span>{t.addCard}</span>
                  </button>
                </div>
              )}

              {/* Cards List (Vertical Scroll) */}
              <div className="flex-1 overflow-y-auto p-3 space-y-2.5 custom-scrollbar min-h-[100px]">
                {column.cards.length === 0 ? (
                  <div className="py-8 text-center text-xs text-black dark:text-slate-300 font-semibold italic">
                    {t.noCardsYet}
                  </div>
                ) : (
                  column.cards.map((card: Card) => {
                    const priorityStyle = getPriorityStyle(card.priority);
                    const isCardOverdue =
                      card.due_date &&
                      new Date(card.due_date) < new Date() &&
                      !(column.title_ru?.toLowerCase().includes('готов') || column.title_ru?.toLowerCase().includes('done'));

                    const cardTitle = getLocalizedText(card, 'title', lang, false);

                    return (
                      <div
                        key={card.id}
                        draggable={board.permissions.can_move_cards}
                        onDragStart={(e) => handleDragStart(card.id, e)}
                        onClick={() => setSelectedCardId(card.id)}
                        className={`group relative p-3.5 rounded-xl bg-white dark:bg-slate-850 border border-slate-300 dark:border-slate-800 shadow-sm hover:shadow-md hover:border-blue-400 dark:hover:border-blue-700 transition cursor-pointer select-none ${
                          draggedCardId === card.id ? 'opacity-40' : ''
                        }`}
                      >
                        {/* Header: Priority & Overdue warning */}
                        <div className="flex items-center justify-between gap-2 mb-2">
                          <span
                            className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-extrabold border ${priorityStyle.pill}`}
                          >
                            <span className={`w-1.5 h-1.5 rounded-full ${priorityStyle.dot}`} />
                            {priorityStyle.label}
                          </span>

                          {card.due_date && (
                            <span
                              className={`inline-flex items-center gap-1 text-[10px] font-bold ${
                                isCardOverdue
                                  ? 'text-black dark:text-white bg-rose-100 dark:bg-rose-950/60 px-1.5 py-0.5 rounded border border-rose-300 dark:border-rose-900/50'
                                  : 'text-black dark:text-white'
                              }`}
                            >
                              <Clock className="w-3 h-3 text-black dark:text-white" />
                              {new Date(card.due_date).toLocaleDateString([], { month: 'short', day: 'numeric' })}
                            </span>
                          )}
                        </div>

                        {/* Title */}
                        <h4 className="text-xs sm:text-sm font-extrabold text-black dark:text-white group-hover:text-blue-700 dark:group-hover:text-blue-400 transition leading-snug">
                          {cardTitle}
                        </h4>

                        {/* Checklist Progress Bar */}
                        {card.checklists_summary && card.checklists_summary.total > 0 && (
                          <div className="mt-2.5">
                            <div className="flex items-center justify-between text-[10px] text-black dark:text-slate-200 font-bold mb-1">
                              <span className="flex items-center gap-1">
                                <CheckSquare className="w-3 h-3 text-black dark:text-slate-200" />
                                Чек-лист
                              </span>
                              <span>
                                {card.checklists_summary.completed}/{card.checklists_summary.total}
                              </span>
                            </div>
                            <div className="h-1.5 w-full bg-slate-200 dark:bg-slate-800 rounded-full overflow-hidden">
                              <div
                                className="h-full bg-emerald-600 rounded-full"
                                style={{
                                  width: `${(card.checklists_summary.completed / card.checklists_summary.total) * 100}%`,
                                }}
                              />
                            </div>
                          </div>
                        )}

                        {/* Footer Badges & Assignees */}
                        <div className="mt-3 pt-2 border-t border-slate-200 dark:border-slate-800/80 flex items-center justify-between gap-2">
                          {/* Badges: Comments & Attachments */}
                          <div className="flex items-center gap-2.5 text-[11px] text-black dark:text-slate-200 font-bold">
                            {card.comments_count > 0 && (
                              <span className="flex items-center gap-1 hover:text-blue-700 dark:hover:text-slate-300">
                                <MessageSquare className="w-3.5 h-3.5 text-black dark:text-slate-200" />
                                {card.comments_count}
                              </span>
                            )}
                            {card.attachments_count > 0 && (
                              <span className="flex items-center gap-1 hover:text-blue-700 dark:hover:text-slate-300">
                                <Paperclip className="w-3.5 h-3.5 text-black dark:text-slate-200" />
                                {card.attachments_count}
                              </span>
                            )}
                          </div>

                          {/* Assignees Avatars Stack */}
                          <div className="flex items-center -space-x-1 overflow-hidden">
                            {card.assignees?.map((a) => (
                              <div
                                key={a.id}
                                title={localizePersonName(a.full_name, lang)}
                                className="h-5 w-5 rounded-full bg-blue-700 text-white font-bold text-[9px] flex items-center justify-center ring-1 ring-white dark:ring-slate-900 shadow-sm"
                              >
                                {a.full_name.charAt(0)}
                              </div>
                            ))}
                          </div>
                        </div>
                      </div>
                    );
                  })
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Modal: Add Column */}
      {showAddColumnModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/70 backdrop-blur-sm animate-in fade-in">
          <div className="w-full max-w-md rounded-2xl bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-800 p-6 shadow-2xl">
            <h3 className="text-base font-black text-black dark:text-white mb-3">
              {t.addColumn}
            </h3>
            <form onSubmit={handleCreateColumn} className="space-y-4">
              <div>
                <label className="text-xs font-bold text-black dark:text-slate-100 uppercase tracking-wider block mb-1">
                  Название раздела
                </label>
                <input
                  type="text"
                  value={newColumnTitle}
                  onChange={(e) => setNewColumnTitle(e.target.value)}
                  placeholder="Например: В процессе тестирования"
                  className="w-full text-xs sm:text-sm p-3 rounded-xl border border-slate-400 dark:border-slate-700 bg-white dark:bg-slate-800 text-black dark:text-white placeholder:text-slate-500 font-medium focus:outline-none focus:ring-2 focus:ring-blue-500/20"
                  autoFocus
                />
                <p className="text-[11px] text-slate-800 dark:text-slate-300 font-semibold mt-1">
                  Название автоматически переведётся на русский, китайский и кыргызский языки.
                </p>
              </div>

              <div>
                <label className="text-xs font-bold text-black dark:text-slate-100 uppercase tracking-wider block mb-1">
                  Расположение раздела
                </label>
                <select
                  value={newColumnPosition}
                  onChange={(e) => setNewColumnPosition(e.target.value)}
                  className="w-full text-xs sm:text-sm p-3 rounded-xl border border-slate-400 dark:border-slate-700 bg-white dark:bg-slate-800 text-black dark:text-white font-medium focus:outline-none focus:ring-2 focus:ring-blue-500/20"
                >
                  <option value="end">В конец списка (по умолчанию)</option>
                  <option value="start">В самое начало</option>
                  {board?.columns?.map((col) => (
                    <option key={col.id} value={`before_${col.id}`}>
                      Перед разделом: {getLocalizedText(col, 'title', lang, false)}
                    </option>
                  ))}
                </select>
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowAddColumnModal(false)}
                  className="px-4 py-2 rounded-xl border border-slate-400 dark:border-slate-700 text-xs font-bold text-black dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition"
                >
                  {t.cancel}
                </button>
                <button
                  type="submit"
                  disabled={!newColumnTitle.trim()}
                  className="px-4 py-2 rounded-xl bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-xs font-bold shadow-sm transition"
                >
                  {t.save}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal: Quick Add Card */}
      {addingCardColumnId !== null && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/70 backdrop-blur-sm animate-in fade-in">
          <div className="w-full max-w-lg rounded-2xl bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-800 p-6 shadow-2xl">
            <h3 className="text-base font-black text-black dark:text-white mb-3">
              {t.addCard}
            </h3>
            <form onSubmit={handleCreateCard} className="space-y-4">
              <div>
                <label className="text-xs font-bold text-black dark:text-slate-100 uppercase tracking-wider block mb-1">
                  {t.cardTitle} *
                </label>
                <input
                  type="text"
                  value={newCardTitle}
                  onChange={(e) => setNewCardTitle(e.target.value)}
                  placeholder="Коротко сформулируйте задачу"
                  className="w-full text-xs sm:text-sm p-3 rounded-xl border border-slate-400 dark:border-slate-700 bg-white dark:bg-slate-800 text-black dark:text-white placeholder:text-slate-500 font-medium focus:outline-none focus:ring-2 focus:ring-blue-500/20"
                  autoFocus
                />
              </div>

              <div>
                <label className="text-xs font-bold text-black dark:text-slate-100 uppercase tracking-wider block mb-1">
                  {t.cardDescription}
                </label>
                <textarea
                  value={newCardDesc}
                  onChange={(e) => setNewCardDesc(e.target.value)}
                  rows={3}
                  placeholder="Критерии приёмки, контекст, ссылки..."
                  className="w-full text-xs sm:text-sm p-3 rounded-xl border border-slate-400 dark:border-slate-700 bg-white dark:bg-slate-800 text-black dark:text-white placeholder:text-slate-500 font-medium focus:outline-none focus:ring-2 focus:ring-blue-500/20 resize-none"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-bold text-black dark:text-slate-100 uppercase tracking-wider block mb-1">
                    {t.priority}
                  </label>
                  <select
                    value={newCardPriority}
                    onChange={(e) => setNewCardPriority(e.target.value as PriorityType)}
                    className="w-full text-xs p-2.5 rounded-xl border border-slate-400 dark:border-slate-700 bg-white dark:bg-slate-800 text-black dark:text-white font-medium"
                  >
                    <option value="urgent">{t.priorityUrgent}</option>
                    <option value="high">{t.priorityHigh}</option>
                    <option value="medium">{t.priorityMedium}</option>
                    <option value="low">{t.priorityLow}</option>
                  </select>
                </div>

                <div>
                  <label className="text-xs font-bold text-black dark:text-slate-100 uppercase tracking-wider block mb-1">
                    {t.dueDate}
                  </label>
                  <input
                    type="date"
                    value={newCardDueDate}
                    onChange={(e) => setNewCardDueDate(e.target.value)}
                    className="w-full text-xs p-2.5 rounded-xl border border-slate-400 dark:border-slate-700 bg-white dark:bg-slate-800 text-black dark:text-white font-medium"
                  />
                </div>
              </div>

              {/* Assignees */}
              {board.members.length > 0 && (
                <div>
                  <label className="text-xs font-bold text-black dark:text-slate-100 uppercase tracking-wider block mb-1">
                    {t.assignees}
                  </label>
                  <div className="flex flex-wrap gap-2 max-h-32 overflow-y-auto p-1">
                    {board.members.map((m) => {
                      const isSelected = newCardAssigneeIds.includes(m.user_id);
                      return (
                        <button
                          key={m.user_id}
                          type="button"
                          onClick={() => {
                            if (isSelected) {
                              setNewCardAssigneeIds(newCardAssigneeIds.filter((id) => id !== m.user_id));
                            } else {
                              setNewCardAssigneeIds([...newCardAssigneeIds, m.user_id]);
                            }
                          }}
                          className={`px-2.5 py-1 rounded-lg text-xs font-bold border transition ${
                            isSelected
                              ? 'bg-blue-600 text-white border-blue-600'
                              : 'bg-white dark:bg-slate-800 text-black dark:text-slate-200 border-slate-400 dark:border-slate-700 hover:bg-slate-100'
                          }`}
                        >
                          {localizePersonName(m.full_name, lang)}
                        </button>
                      );
                    })}
                  </div>
                </div>
              )}

              <div className="flex justify-end gap-2 pt-2 border-t border-slate-200 dark:border-slate-800">
                <button
                  type="button"
                  onClick={() => setAddingCardColumnId(null)}
                  className="px-4 py-2 rounded-xl border border-slate-400 dark:border-slate-700 text-xs font-bold text-black dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 transition"
                >
                  {t.cancel}
                </button>
                <button
                  type="submit"
                  disabled={!newCardTitle.trim()}
                  className="px-4 py-2 rounded-xl bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-xs font-bold shadow-sm transition"
                >
                  {t.save}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Card Detail & Comments Modal */}
      {selectedCardId && (
        <CardDetailModal
          cardId={selectedCardId}
          onClose={() => setSelectedCardId(null)}
          onCardUpdated={loadBoard}
          lang={lang}
          currentUser={currentUser}
          columns={board?.columns || []}
          onMoveCard={handleMoveCardDirectly}
        />
      )}
    </div>
  );
};
