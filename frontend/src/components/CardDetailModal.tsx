'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { Column, LanguageCode, User, ChecklistItem, Comment, Attachment, ActivityLog } from '@/types';
import { 
  translations, 
  getLocalizedText, 
  localizePersonName, 
  localizeRole, 
  localizeDynamicText 
} from '@/lib/i18n';
import { api } from '@/lib/api';
import {
  X,
  Calendar,
  Clock,
  User as UserIcon,
  Tag,
  CheckSquare,
  Paperclip,
  MessageSquare,
  History,
  Trash2,
  Plus,
  Send,
  Download,
  FileText,
  Image as ImageIcon,
  Globe,
  Eye,
  EyeOff
} from 'lucide-react';

interface CardDetailModalProps {
  cardId: number | null;
  onClose: () => void;
  onCardUpdated: () => void;
  lang: LanguageCode;
  currentUser: User | null;
  columns?: Column[];
  onMoveCard?: (cardId: number, targetColId: number) => Promise<void>;
}

export const CardDetailModal: React.FC<CardDetailModalProps> = ({
  cardId,
  onClose,
  onCardUpdated,
  lang,
  currentUser,
  columns,
  onMoveCard,
}) => {
  const t = translations[lang] || translations.ru;
  const [loading, setLoading] = useState(true);
  const [cardData, setCardData] = useState<any>(null);
  const [showOriginal, setShowOriginal] = useState(false);
  const [selectedLangTab, setSelectedLangTab] = useState<'current' | 'ru' | 'zh' | 'ky'>('current');

  // Edit fields
  const [title, setTitle] = useState('');
  const [desc, setDesc] = useState('');
  const [priority, setPriority] = useState<string>('medium');
  const [dueDate, setDueDate] = useState<string>('');
  const [selectedAssigneeIds, setSelectedAssigneeIds] = useState<number[]>([]);

  // Checklist input
  const [newChecklistTitle, setNewChecklistTitle] = useState('');

  // Comment input
  const [newCommentText, setNewCommentText] = useState('');
  const [commentShowOriginalMap, setCommentShowOriginalMap] = useState<Record<number, boolean>>({});

  // File upload state
  const [uploadingFile, setUploadingFile] = useState(false);

  const loadCardDetails = useCallback(async (id: number) => {
    try {
      setLoading(true);
      const data = await api.getCardDetail(id);
      setCardData(data);
      setTitle(getLocalizedText(data, 'title', lang, false));
      setDesc(getLocalizedText(data, 'desc', lang, false));
      setPriority(data.priority);
      setDueDate(data.due_date ? data.due_date.split('T')[0] : '');
      setSelectedAssigneeIds(data.assignees.map((a: any) => a.id));
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, [lang]);

  useEffect(() => {
    if (cardId) {
      loadCardDetails(cardId);
    }
  }, [cardId, loadCardDetails]);

  if (!cardId) return null;

  const canManage = cardData?.permissions?.can_manage_card ?? false;
  const canComment = cardData?.permissions?.can_comment ?? true;
  const canMove = cardData?.permissions?.can_move_card ?? true;

  const handleSaveBasicInfo = async () => {
    if (!canManage) return;
    try {
      await api.updateCard(cardId, {
        title,
        description: desc,
        priority,
        due_date: dueDate || null,
        assignee_ids: selectedAssigneeIds,
        language: lang === 'zh-Hans' || lang === 'zh-Hant' ? 'zh' : lang,
      });
      await loadCardDetails(cardId);
      onCardUpdated();
    } catch (err: any) {
      alert(err.message || 'Ошибка обновления карточки');
    }
  };

  const handleAttachmentDownload = async (attachment: Attachment) => {
    try {
      await api.downloadAttachment(attachment.id, attachment.file_name);
    } catch (error) {
      alert(error instanceof Error ? error.message : t.attachments);
    }
  };

  const handleMoveToColumn = async (newColId: number) => {
    if (!cardId || !cardData || cardData.column_id === newColId) return;
    const oldColId = cardData.column_id;
    const targetCol = columns?.find((c) => c.id === newColId);

    // Optimistically update cardData in modal state immediately
    setCardData({
      ...cardData,
      column_id: newColId,
      column_title_ru: targetCol?.title_ru || cardData.column_title_ru,
      column_title_zh: targetCol?.title_zh || cardData.column_title_zh,
      column_title_ky: targetCol?.title_ky || cardData.column_title_ky,
    });

    if (onMoveCard) {
      await onMoveCard(cardId, newColId);
    } else {
      try {
        await api.moveCard(cardId, newColId, 0);
        onCardUpdated();
      } catch (err: any) {
        setCardData({
          ...cardData,
          column_id: oldColId,
        });
        alert(err.message || 'Ошибка перемещения карточки');
      }
    }
  };

  const handleToggleChecklist = async (itemId: number) => {
    if (!cardData) return;
    const prevChecklists = cardData.checklists;
    // Optimistic toggle (0ms latency)
    const nextChecklists = cardData.checklists.map((item: any) =>
      item.id === itemId ? { ...item, is_completed: !item.is_completed } : item
    );
    setCardData({
      ...cardData,
      checklists: nextChecklists,
    });
    onCardUpdated();

    try {
      await api.toggleChecklistItem(itemId);
    } catch (err: any) {
      setCardData({
        ...cardData,
        checklists: prevChecklists,
      });
      onCardUpdated();
      alert(err.message || 'Ошибка обновления чек-листа');
    }
  };

  const handleAddChecklist = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newChecklistTitle.trim()) return;
    const titleText = newChecklistTitle.trim();
    setNewChecklistTitle('');

    try {
      const newItem = await api.addChecklistItem(cardId, titleText);
      if (cardData) {
        setCardData({
          ...cardData,
          checklists: [...(cardData.checklists || []), newItem],
        });
      }
      onCardUpdated();
    } catch (err: any) {
      alert(err.message || 'Ошибка добавления пункта чек-листа');
      await loadCardDetails(cardId);
    }
  };

  const handleDeleteChecklist = async (itemId: number) => {
    if (!cardData) return;
    const prevChecklists = cardData.checklists;
    setCardData({
      ...cardData,
      checklists: cardData.checklists.filter((i: any) => i.id !== itemId),
    });
    onCardUpdated();

    try {
      await api.deleteChecklistItem(itemId);
    } catch (err: any) {
      setCardData({
        ...cardData,
        checklists: prevChecklists,
      });
      onCardUpdated();
      alert(err.message || 'Ошибка удаления пункта чек-листа');
    }
  };

  const handleAddComment = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newCommentText.trim()) return;
    try {
      await api.addComment(
        cardId,
        newCommentText.trim(),
        lang === 'zh-Hans' || lang === 'zh-Hant' ? 'zh' : lang
      );
      setNewCommentText('');
      await loadCardDetails(cardId);
      onCardUpdated();
    } catch (err: any) {
      alert(err.message || 'Ошибка добавления комментария');
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    try {
      setUploadingFile(true);
      await api.uploadAttachment(cardId, file);
      await loadCardDetails(cardId);
      onCardUpdated();
    } catch (err: any) {
      alert(err.message || 'Ошибка загрузки файла');
    } finally {
      setUploadingFile(false);
      e.target.value = '';
    }
  };

  const handleDeleteAttachment = async (attachmentId: number) => {
    try {
      await api.deleteAttachment(attachmentId);
      await loadCardDetails(cardId);
      onCardUpdated();
    } catch (err: any) {
      alert(err.message || 'Ошибка удаления вложения');
    }
  };

  const handleDeleteCard = async () => {
    if (!confirm(t.confirmDelete)) return;
    try {
      await api.deleteCard(cardId);
      onCardUpdated();
      onClose();
    } catch (err: any) {
      alert(err.message || 'Ошибка удаления карточки');
    }
  };

  const getPriorityBadge = (p: string) => {
    switch (p) {
      case 'urgent':
        return { label: t.priorityUrgent, color: 'bg-rose-100 dark:bg-rose-950/60 text-black dark:text-white border-rose-300 dark:border-rose-800' };
      case 'high':
        return { label: t.priorityHigh, color: 'bg-amber-100 dark:bg-amber-950/60 text-black dark:text-white border-amber-300 dark:border-amber-800' };
      case 'low':
        return { label: t.priorityLow, color: 'bg-slate-200 dark:bg-slate-800 text-black dark:text-white border-slate-300 dark:border-slate-700' };
      case 'medium':
      default:
        return { label: t.priorityMedium, color: 'bg-blue-100 dark:bg-blue-950/60 text-black dark:text-white border-blue-300 dark:border-blue-800' };
    }
  };

  const isOverdue =
    cardData?.due_date &&
    new Date(cardData.due_date) < new Date() &&
    !(cardData.column_title_ru?.toLowerCase().includes('готов') || cardData.column_title_ru?.toLowerCase().includes('done'));

  const checklistTotal = cardData?.checklists?.length || 0;
  const checklistCompleted = cardData?.checklists?.filter((i: any) => i.is_completed).length || 0;
  const checklistPercent = checklistTotal > 0 ? Math.round((checklistCompleted / checklistTotal) * 100) : 0;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-6 bg-slate-950/60 backdrop-blur-sm animate-in fade-in duration-200">
      <div 
        className="relative w-full max-w-4xl max-h-[92vh] overflow-hidden rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-2xl flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        {loading ? (
          <div className="p-12 flex flex-col items-center justify-center gap-3">
            <div className="w-8 h-8 rounded-full border-2 border-blue-500 border-t-transparent animate-spin" />
            <p className="text-xs text-slate-400">Загрузка данных задачи...</p>
          </div>
        ) : (
          <>
            {/* Modal Header */}
            <div className="flex items-center justify-between px-6 py-4 border-b border-slate-300 dark:border-slate-800 bg-slate-100/70 dark:bg-slate-850/50">
              <div className="flex items-center gap-2.5 flex-wrap">
                {columns && columns.length > 0 && canMove ? (
                  <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-blue-100 dark:bg-blue-950/60 border border-blue-300 dark:border-blue-800">
                    <span className="text-[11px] font-bold text-black dark:text-white">Этап:</span>
                    <select
                      value={cardData.column_id}
                      onChange={(e) => handleMoveToColumn(Number(e.target.value))}
                      className="text-xs font-black bg-transparent text-black dark:text-white focus:outline-none cursor-pointer"
                    >
                      {columns.map((c) => (
                        <option
                          key={c.id}
                          value={c.id}
                          className="text-black dark:text-white bg-white dark:bg-slate-900 font-bold"
                        >
                          {getLocalizedText(c, 'title', lang, false)}
                        </option>
                      ))}
                    </select>
                  </div>
                ) : (
                  <span className="px-2.5 py-1 text-xs font-bold rounded-lg bg-blue-100 text-black dark:bg-blue-950/60 dark:text-white border border-blue-300 dark:border-blue-800">
                    {getLocalizedText(cardData, 'column_title' as any, lang, false) || cardData.column_title_ru}
                  </span>
                )}

                <span className="text-xs font-bold text-black dark:text-slate-200 flex items-center gap-1">
                  <Globe className="w-3.5 h-3.5 text-blue-600" />
                  Язык оригинала: <strong className="uppercase text-black dark:text-white font-extrabold">{cardData.original_lang}</strong>
                </span>

                <button
                  type="button"
                  onClick={() => setShowOriginal(!showOriginal)}
                  className={`flex items-center gap-1.5 px-2.5 py-1 text-xs font-bold rounded-lg border transition ${
                    showOriginal
                      ? 'bg-amber-100 dark:bg-amber-950/60 text-amber-950 dark:text-amber-200 border-amber-400 dark:border-amber-700'
                      : 'bg-white dark:bg-slate-800 text-black dark:text-white border-slate-400 dark:border-slate-700 hover:bg-slate-100'
                  }`}
                >
                  {showOriginal ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
                  {showOriginal ? t.showingOriginal : t.showOriginal}
                </button>
              </div>

              <button
                type="button"
                onClick={onClose}
                className="p-1.5 rounded-lg text-black hover:text-blue-600 dark:text-slate-200 dark:hover:text-white hover:bg-slate-200 dark:hover:bg-slate-800 transition"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Modal Body */}
            <div className="flex-1 overflow-y-auto p-6 grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Main Content (2 Cols) */}
              <div className="lg:col-span-2 space-y-6">
                {/* Title & Desc */}
                <div>
                  {canManage ? (
                    <div className="space-y-3">
                      <input
                        type="text"
                        value={title}
                        onChange={(e) => setTitle(e.target.value)}
                        onBlur={handleSaveBasicInfo}
                        placeholder={t.cardTitle}
                        className="w-full text-lg sm:text-xl font-black bg-transparent border-b border-slate-300 hover:border-slate-500 focus:border-blue-600 focus:outline-none py-1 text-black dark:text-white transition"
                      />
                      <textarea
                        value={desc}
                        onChange={(e) => setDesc(e.target.value)}
                        onBlur={handleSaveBasicInfo}
                        rows={3}
                        placeholder={t.cardDescription}
                        className="w-full text-xs sm:text-sm font-medium p-3 rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800/50 text-black dark:text-white placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500/20 resize-none transition"
                      />
                    </div>
                  ) : (
                    <div>
                      <h2 className="text-xl font-black text-black dark:text-white leading-snug">
                        {showOriginal
                          ? (cardData[`title_${cardData.original_lang}`] || cardData.title_ru)
                          : getLocalizedText(cardData, 'title', lang, false)}
                      </h2>
                      <p className="mt-2 text-xs sm:text-sm font-medium text-black dark:text-slate-200 leading-relaxed whitespace-pre-wrap">
                        {showOriginal
                          ? (cardData[`desc_${cardData.original_lang}`] || cardData.desc_ru)
                          : (getLocalizedText(cardData, 'desc', lang, false) || 'Нет описания')}
                      </p>
                    </div>
                  )}
                </div>

                {/* Multilingual Preview Tabs */}
                <div className="rounded-xl border border-slate-300 dark:border-slate-800 p-3 bg-slate-50 dark:bg-slate-850/40">
                  <div className="flex items-center justify-between pb-2 border-b border-slate-200 dark:border-slate-800">
                    <span className="text-xs font-bold text-black dark:text-white flex items-center gap-1.5">
                      <Globe className="w-3.5 h-3.5 text-blue-600" />
                      Мультиязычный автоперевод (RU, ZH, KY)
                    </span>
                    <div className="flex items-center gap-1">
                      {(['ru', 'zh', 'ky'] as const).map((code) => (
                        <button
                          key={code}
                          type="button"
                          onClick={() => setSelectedLangTab(code)}
                          className={`px-2 py-0.5 rounded text-[11px] font-black uppercase transition ${
                            selectedLangTab === code
                              ? 'bg-blue-600 text-white'
                              : 'bg-slate-200 dark:bg-slate-700 text-black dark:text-slate-200 hover:bg-slate-300'
                          }`}
                        >
                          {code}
                        </button>
                      ))}
                    </div>
                  </div>
                  <div className="pt-2 text-xs text-black dark:text-slate-200">
                    {selectedLangTab === 'current' ? (
                      <p className="font-semibold italic text-slate-800 dark:text-slate-300">
                        Текст автоматически переведён на русский, китайский и кыргызский языки. Нажмите вкладку выше для просмотра других переводов.
                      </p>
                    ) : (
                      <div className="space-y-1">
                        <div className="font-bold text-black dark:text-white">
                          {cardData[`title_${selectedLangTab}`] || '—'}
                        </div>
                        <div className="text-[11px] text-slate-900 dark:text-slate-200 font-medium whitespace-pre-wrap">
                          {cardData[`desc_${selectedLangTab}`] || '—'}
                        </div>
                      </div>
                    )}
                  </div>
                </div>

                {/* Checklist Section */}
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <CheckSquare className="w-4 h-4 text-black dark:text-slate-200" />
                      <span className="text-xs font-black text-black dark:text-white uppercase tracking-wider">
                        {t.checklists} ({checklistCompleted}/{checklistTotal})
                      </span>
                    </div>
                    {checklistTotal > 0 && (
                      <span className="text-xs font-extrabold text-black dark:text-white">{checklistPercent}%</span>
                    )}
                  </div>

                  {checklistTotal > 0 && (
                    <div className="h-1.5 w-full bg-slate-200 dark:bg-slate-800 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-emerald-600 transition-all duration-300"
                        style={{ width: `${checklistPercent}%` }}
                      />
                    </div>
                  )}

                  <div className="space-y-1.5">
                    {cardData?.checklists?.map((item: ChecklistItem) => (
                      <div
                        key={item.id}
                        className="flex items-center justify-between p-2 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800/60 transition group"
                      >
                        <label className="flex items-center gap-2.5 cursor-pointer flex-1">
                          <input
                            type="checkbox"
                            checked={item.is_completed}
                            onChange={() => handleToggleChecklist(item.id)}
                            className="w-4 h-4 rounded border-slate-400 text-blue-600 focus:ring-blue-500 cursor-pointer"
                          />
                          <span
                            className={`text-xs sm:text-sm font-bold ${
                              item.is_completed
                                ? 'line-through text-slate-500 dark:text-slate-400'
                                : 'text-black dark:text-white'
                            }`}
                          >
                            {localizeDynamicText(item.title, lang)}
                          </span>
                        </label>
                        {canMove && (
                          <button
                            type="button"
                            onClick={() => handleDeleteChecklist(item.id)}
                            className="opacity-0 group-hover:opacity-100 p-1 text-slate-500 hover:text-rose-600 transition"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        )}
                      </div>
                    ))}
                  </div>

                  {canMove && (
                    <form onSubmit={handleAddChecklist} className="flex items-center gap-2 mt-2">
                      <input
                        type="text"
                        value={newChecklistTitle}
                        onChange={(e) => setNewChecklistTitle(e.target.value)}
                        placeholder={t.addChecklistItem}
                        className="flex-1 text-xs px-3 py-1.5 rounded-lg border border-slate-400 dark:border-slate-700 bg-white dark:bg-slate-800 text-black dark:text-white font-medium focus:outline-none focus:ring-2 focus:ring-blue-500/20"
                      />
                      <button
                        type="submit"
                        disabled={!newChecklistTitle.trim()}
                        className="px-3 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-xs font-bold transition"
                      >
                        <Plus className="w-3.5 h-3.5" />
                      </button>
                    </form>
                  )}
                </div>

                {/* Attachments Section */}
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Paperclip className="w-4 h-4 text-black dark:text-slate-200" />
                      <span className="text-xs font-black text-black dark:text-white uppercase tracking-wider">
                        {t.attachments} ({cardData?.attachments?.length || 0})
                      </span>
                    </div>

                    <label className="cursor-pointer px-2.5 py-1 text-xs font-bold rounded-lg border border-slate-400 dark:border-slate-700 bg-white dark:bg-slate-800 hover:bg-slate-100 text-black dark:text-white flex items-center gap-1.5 transition">
                      <Plus className="w-3.5 h-3.5" />
                      <span>{uploadingFile ? 'Загрузка...' : t.uploadFile}</span>
                      <input
                        type="file"
                        onChange={handleFileUpload}
                        disabled={uploadingFile}
                        className="hidden"
                      />
                    </label>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                    {cardData?.attachments?.map((att: Attachment) => {
                      const isImg = att.content_type?.startsWith('image/');
                      return (
                        <div
                          key={att.id}
                          className="flex items-center justify-between p-2.5 rounded-xl border border-slate-300 dark:border-slate-800 bg-white dark:bg-slate-850/60 hover:border-slate-400 transition"
                        >
                          <div className="flex items-center gap-2.5 min-w-0">
                            <div className="p-2 rounded-lg bg-blue-100 dark:bg-blue-950/60 text-blue-700 dark:text-blue-400">
                              {isImg ? <ImageIcon className="w-4 h-4" /> : <FileText className="w-4 h-4" />}
                            </div>
                            <div className="min-w-0">
                              <button
                                type="button"
                                onClick={() => handleAttachmentDownload(att)}
                                className="block max-w-full text-left text-xs font-bold text-black dark:text-white truncate hover:text-blue-700 hover:underline"
                              >
                                {att.file_name}
                              </button>
                              <div className="text-[10px] text-slate-800 dark:text-slate-300 font-semibold">
                                {Math.round(att.file_size / 1024)} KB • {att.uploader_name}
                              </div>
                            </div>
                          </div>

                          <div className="flex items-center gap-1">
                            <button
                              type="button"
                              aria-label={`Download ${att.file_name}`}
                              onClick={() => handleAttachmentDownload(att)}
                              className="p-1 text-black hover:text-blue-700 dark:text-slate-300 transition"
                            >
                              <Download className="w-3.5 h-3.5" />
                            </button>
                            {canMove && (
                              <button
                                type="button"
                                onClick={() => handleDeleteAttachment(att.id)}
                                aria-label={`Delete ${att.file_name}`}
                                className="p-1 text-slate-500 hover:text-rose-600 transition"
                              >
                                <Trash2 className="w-3.5 h-3.5" />
                              </button>
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>

                {/* Comments Section */}
                <div className="space-y-4 pt-4 border-t border-slate-300 dark:border-slate-800">
                  <div className="flex items-center gap-2">
                    <MessageSquare className="w-4 h-4 text-black dark:text-slate-200" />
                    <span className="text-xs font-black text-black dark:text-white uppercase tracking-wider">
                      {t.comments} ({cardData?.comments?.length || 0})
                    </span>
                  </div>

                  {/* Add comment input */}
                  {canComment && (
                    <form onSubmit={handleAddComment} className="flex items-start gap-2.5">
                      <div className="h-8 w-8 rounded-full bg-slate-900 text-white font-bold text-xs flex items-center justify-center flex-shrink-0 mt-0.5">
                        {currentUser?.full_name?.charAt(0) || 'U'}
                      </div>
                      <div className="flex-1 space-y-2">
                        <textarea
                          value={newCommentText}
                          onChange={(e) => setNewCommentText(e.target.value)}
                          placeholder={t.addComment}
                          rows={2}
                          className="w-full text-xs sm:text-sm font-medium p-3 rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-black dark:text-white placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500/20 resize-none transition"
                        />
                        <div className="flex justify-end">
                          <button
                            type="submit"
                            disabled={!newCommentText.trim()}
                            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-xs font-bold shadow-sm transition"
                          >
                            <Send className="w-3.5 h-3.5" />
                            <span>{t.save}</span>
                          </button>
                        </div>
                      </div>
                    </form>
                  )}

                  {/* Comments Thread */}
                  <div className="space-y-3">
                    {cardData?.comments?.map((c: Comment) => {
                      const showOrig = commentShowOriginalMap[c.id] || false;
                      const commentText = showOrig
                        ? (c[`text_${c.original_lang}` as keyof Comment] || c.text_ru)
                        : getLocalizedText(c, 'text', lang, false);

                      return (
                        <div
                          key={c.id}
                          className="flex items-start gap-3 p-3 rounded-xl bg-white dark:bg-slate-850/60 border border-slate-300 dark:border-slate-800 shadow-sm"
                        >
                          <div className="h-7 w-7 rounded-full bg-slate-800 text-white font-bold text-xs flex items-center justify-center flex-shrink-0">
                            {c.user_full_name?.charAt(0) || 'U'}
                          </div>
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center justify-between gap-2">
                              <div className="flex items-center gap-2">
                                <span className="font-extrabold text-xs text-black dark:text-white">
                                  {localizePersonName(c.user_full_name, lang)}
                                </span>
                                {c.user_role && (
                                  <span className="text-[10px] font-bold px-1.5 py-0.2 rounded bg-slate-200 dark:bg-slate-700 text-black dark:text-slate-200">
                                    {localizeRole(c.user_role, lang)}
                                  </span>
                                )}
                              </div>
                              <span className="text-[10px] text-slate-800 dark:text-slate-400 font-semibold">
                                {c.created_at ? new Date(c.created_at).toLocaleDateString() : ''}
                              </span>
                            </div>

                            <p className="mt-1 text-xs text-black dark:text-slate-100 font-medium leading-relaxed whitespace-pre-wrap">
                              {commentText}
                            </p>

                            <div className="mt-2 flex items-center gap-2">
                              <button
                                type="button"
                                onClick={() =>
                                  setCommentShowOriginalMap({
                                    ...commentShowOriginalMap,
                                    [c.id]: !showOrig,
                                  })
                                }
                                className="text-[11px] text-blue-700 dark:text-blue-400 font-bold hover:underline flex items-center gap-1"
                              >
                                {showOrig ? t.showingOriginal : `${t.showOriginal} (${c.original_lang.toUpperCase()})`}
                              </button>
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>

              {/* Sidebar Properties (1 Col) */}
              <div className="space-y-6 lg:border-l lg:border-slate-300 lg:dark:border-slate-800 lg:pl-6">
                {/* Priority */}
                <div className="space-y-1.5">
                  <label className="text-xs font-black text-black dark:text-slate-100 uppercase tracking-wider flex items-center gap-1.5">
                    <Tag className="w-3.5 h-3.5 text-blue-600" />
                    {t.priority}
                  </label>
                  {canManage ? (
                    <select
                      value={priority}
                      onChange={(e) => {
                        setPriority(e.target.value);
                        api.updateCard(cardId, { priority: e.target.value }).then(() => {
                          loadCardDetails(cardId);
                          onCardUpdated();
                        });
                      }}
                      className="w-full text-xs font-bold p-2 rounded-lg border border-slate-400 dark:border-slate-700 bg-white dark:bg-slate-800 text-black dark:text-white"
                    >
                      <option value="urgent">{t.priorityUrgent}</option>
                      <option value="high">{t.priorityHigh}</option>
                      <option value="medium">{t.priorityMedium}</option>
                      <option value="low">{t.priorityLow}</option>
                    </select>
                  ) : (
                    <div className={`inline-block px-2.5 py-1 rounded-md text-xs font-bold border ${getPriorityBadge(cardData?.priority).color}`}>
                      {getPriorityBadge(cardData?.priority).label}
                    </div>
                  )}
                </div>

                {/* Due Date */}
                <div className="space-y-1.5">
                  <label className="text-xs font-black text-black dark:text-slate-100 uppercase tracking-wider flex items-center gap-1.5">
                    <Calendar className="w-3.5 h-3.5 text-blue-600" />
                    {t.dueDate}
                  </label>
                  {canManage ? (
                    <input
                      type="date"
                      value={dueDate}
                      onChange={(e) => {
                        setDueDate(e.target.value);
                        api.updateCard(cardId, { due_date: e.target.value || null }).then(() => {
                          loadCardDetails(cardId);
                          onCardUpdated();
                        });
                      }}
                      className="w-full text-xs font-bold p-2 rounded-lg border border-slate-400 dark:border-slate-700 bg-white dark:bg-slate-800 text-black dark:text-white"
                    />
                  ) : (
                    <div className={`text-xs font-bold flex items-center gap-1.5 ${isOverdue ? 'text-rose-700 font-extrabold' : 'text-black dark:text-white'}`}>
                      <Clock className="w-3.5 h-3.5" />
                      {cardData?.due_date ? new Date(cardData.due_date).toLocaleDateString() : '—'}
                      {isOverdue && <span className="text-[10px] px-1.5 py-0.5 rounded bg-rose-100 text-rose-800 dark:bg-rose-900/50 dark:text-rose-300 font-extrabold">{t.overdue}</span>}
                    </div>
                  )}
                </div>

                {/* Assignees */}
                <div className="space-y-2">
                  <label className="text-xs font-black text-black dark:text-slate-100 uppercase tracking-wider flex items-center gap-1.5">
                    <UserIcon className="w-3.5 h-3.5 text-blue-600" />
                    {t.assignees}
                  </label>

                  <div className="flex flex-wrap gap-1.5">
                    {cardData?.assignees?.map((a: any) => (
                      <span
                        key={a.id}
                        className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-bold bg-white dark:bg-slate-800 text-black dark:text-white border border-slate-400 dark:border-slate-700 shadow-sm"
                      >
                        <span className="w-4 h-4 rounded-full bg-blue-600 text-white text-[9px] font-bold flex items-center justify-center">
                          {a.full_name.charAt(0)}
                        </span>
                        {localizePersonName(a.full_name, lang)}
                      </span>
                    ))}
                  </div>

                  {canManage && cardData?.available_assignees?.length > 0 && (
                    <div className="pt-2 border-t border-slate-200 dark:border-slate-800">
                      <span className="text-[11px] font-bold text-black dark:text-slate-200 block mb-1">Назначить участника:</span>
                      <div className="space-y-1 max-h-36 overflow-y-auto">
                        {cardData.available_assignees.map((u: any) => {
                          const isAssigned = selectedAssigneeIds.includes(u.id);
                          return (
                            <label
                              key={u.id}
                              className="flex items-center justify-between p-1.5 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 text-xs cursor-pointer font-bold text-black dark:text-white"
                            >
                              <span>{localizePersonName(u.full_name, lang)}</span>
                              <input
                                type="checkbox"
                                checked={isAssigned}
                                onChange={(e) => {
                                  const newIds = e.target.checked
                                    ? [...selectedAssigneeIds, u.id]
                                    : selectedAssigneeIds.filter((id) => id !== u.id);
                                  setSelectedAssigneeIds(newIds);
                                  api.updateCard(cardId, { assignee_ids: newIds }).then(() => {
                                    loadCardDetails(cardId);
                                    onCardUpdated();
                                  });
                                }}
                                className="w-3.5 h-3.5 rounded text-blue-600"
                              />
                            </label>
                          );
                        })}
                      </div>
                    </div>
                  )}
                </div>

                {/* Activity History Timeline */}
                <div className="space-y-2 pt-4 border-t border-slate-300 dark:border-slate-800">
                  <span className="text-xs font-black text-black dark:text-slate-100 uppercase tracking-wider flex items-center gap-1.5">
                    <History className="w-3.5 h-3.5 text-blue-600" />
                    {t.activityHistory}
                  </span>

                  <div className="space-y-2 max-h-48 overflow-y-auto text-[11px]">
                    {cardData?.activities?.map((act: ActivityLog) => (
                      <div key={act.id} className="p-2 rounded-lg bg-white dark:bg-slate-850/50 border border-slate-300 dark:border-slate-800/60 leading-relaxed shadow-sm">
                        <div className="font-bold text-black dark:text-white">
                          {localizePersonName(act.user_full_name, lang)}: {localizeDynamicText(act.details, lang)}
                        </div>
                        {act.created_at && (
                          <div className="text-[10px] text-slate-800 dark:text-slate-400 font-semibold mt-0.5">
                            {new Date(act.created_at).toLocaleString([], { dateStyle: 'short', timeStyle: 'short' })}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>

                {/* Delete Card Button */}
                {canManage && (
                  <div className="pt-4 border-t border-slate-300 dark:border-slate-800">
                    <button
                      type="button"
                      onClick={handleDeleteCard}
                      className="w-full py-2 px-3 rounded-xl border border-rose-300 dark:border-rose-900/50 bg-rose-50 dark:bg-rose-950/20 text-rose-700 dark:text-rose-400 hover:bg-rose-100 text-xs font-bold flex items-center justify-center gap-2 transition"
                    >
                      <Trash2 className="w-4 h-4" />
                      {t.deleteCard}
                    </button>
                  </div>
                )}
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
};
