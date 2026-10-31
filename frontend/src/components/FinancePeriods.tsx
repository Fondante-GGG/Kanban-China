'use client';

import { useCallback, useEffect, useId, useRef, useState } from 'react';
import { api } from '@/lib/api';
import { financePeriodTranslations } from '@/lib/finance-periods-i18n';
import type { FinancePeriod, FinancePeriodsResponse, LanguageCode } from '@/types';

const base = 'min-h-11 rounded-lg px-3 py-2 text-sm font-semibold focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600 disabled:opacity-50';
const button = `${base} border border-slate-300 hover:bg-slate-100 dark:border-slate-600 dark:hover:bg-slate-800`;
const primary = `${base} border border-blue-700 bg-blue-700 text-white hover:bg-blue-800 dark:border-blue-500 dark:bg-blue-700 dark:hover:bg-blue-800`;
const input = 'min-h-11 min-w-0 w-full rounded-lg border border-slate-500 bg-white px-3 py-2 text-slate-950 dark:border-slate-400 dark:bg-slate-900 dark:text-slate-100 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600';
interface Closing { year: number; month: number; reason: string; uncertain: boolean }
function validYear(value: string) { return /^\d{1,4}$/.test(value) && Number(value) >= 1 && Number(value) <= 9999; }
function validResponse(value: FinancePeriodsResponse, year: number) {
  return value.year === year && typeof value.can_close === 'boolean' && Array.isArray(value.items) && value.items.length === 12
    && new Set(value.items.map(item => item.month)).size === 12
    && value.items.every(item => item.year === year && Number.isInteger(item.month) && item.month >= 1 && item.month <= 12
      && typeof item.is_closed === 'boolean' && typeof item.close_reason === 'string'
      && (item.closed_by_name === null || typeof item.closed_by_name === 'string')
      && (item.closed_at === null || typeof item.closed_at === 'string'));
}

export function FinancePeriods({ lang, userId }: { lang: LanguageCode; userId: number }) {
  const t = financePeriodTranslations[lang], prefix = useId();
  const [year, setYear] = useState(() => Number(new Intl.DateTimeFormat('en', {year:'numeric',timeZone:'Asia/Bishkek'}).format(new Date())));
  const [yearInput, setYearInput] = useState(() => String(year));
  const [data, setData] = useState<FinancePeriodsResponse | null>(null), [loading, setLoading] = useState(true);
  const [denied, setDenied] = useState(false);
  const [error, setError] = useState(''), [yearError, setYearError] = useState(false), [reasonError, setReasonError] = useState(false);
  const [editing, setEditing] = useState<number | null>(null), [reason, setReason] = useState('');
  const [closing, setClosing] = useState<Closing | null>(null), [busy, setBusy] = useState(false), [success, setSuccess] = useState<FinancePeriod | null>(null);
  const mounted = useRef(true), generation = useRef(0), session = useRef(0), posting = useRef(false), forbiddenSession = useRef(false);
  const title = useRef<HTMLHeadingElement>(null), summary = useRef<HTMLFieldSetElement>(null), reasonField = useRef<HTMLTextAreaElement>(null);
  const locale = {ru:'ru-RU',ky:'ky-KG','zh-Hans':'zh-CN','zh-Hant':'zh-TW'}[lang];
  const monthLabel = (period: Pick<FinancePeriod,'year'|'month'>) => {
    const value = new Date(0); value.setUTCFullYear(period.year, period.month - 1, 15);
    return new Intl.DateTimeFormat(locale,{month:'long',year:'numeric',timeZone:'UTC'}).format(value);
  };
  const timestamp = (value: string | null) => {
    if (!value) return '—';
    const parsed = new Date(value);
    return Number.isNaN(parsed.getTime()) ? '—' : new Intl.DateTimeFormat(locale,{dateStyle:'medium',timeStyle:'short',timeZone:'Asia/Bishkek'}).format(parsed);
  };
  const deniedText = useRef(t.forbidden);
  useEffect(() => { deniedText.current = t.forbidden; }, [t.forbidden]);
  const forbidden = useCallback(() => {
    forbiddenSession.current = true; setDenied(true); session.current++; generation.current++;
    setData(null); setEditing(null); setReason(''); setClosing(null); setSuccess(null); setBusy(false); setLoading(false); setError(deniedText.current);
  }, []);
  const load = useCallback(async (signal?: AbortSignal) => {
    if (forbiddenSession.current) return null;
    const request = ++generation.current;
    setLoading(true);
    try {
      const result = await api.getFinancePeriods(year, signal);
      if (!mounted.current || request !== generation.current || forbiddenSession.current) return null;
      if (!validResponse(result, year)) throw new Error('Invalid financial period response');
      setData(result);
      if (!result.can_close) { setEditing(null); setReason(''); setClosing(null); }
      return result;
    } catch (cause) {
      if (!mounted.current || request !== generation.current || signal?.aborted) return null;
      if ([401,403].includes((cause as {status?:number}).status || 0)) forbidden();
      else { setData(null); setError(t.failed); }
      return null;
    } finally { if (mounted.current && request === generation.current) setLoading(false); }
  }, [year, forbidden, t.failed]);
  const invalidate = useCallback(() => { session.current++; generation.current++; }, []);
  useEffect(() => {
    mounted.current = true;
    const authChanged = () => forbidden();
    window.addEventListener('kanban-auth-change', authChanged);
    return () => { mounted.current = false; invalidate(); window.removeEventListener('kanban-auth-change', authChanged); };
  }, [userId, forbidden, invalidate]);
  useEffect(() => {
    const controller = new AbortController(); void load(controller.signal);
    return () => controller.abort();
  }, [load]);
  const focusCard = (month: number) => requestAnimationFrame(() => document.getElementById(`${prefix}-month-${month}`)?.focus());
  const closed = (value: FinancePeriod) => {
    setData(current => current ? {...current, items:current.items.map(item => item.year === value.year && item.month === value.month ? value : item)} : current);
    setEditing(null); setReason(''); setClosing(null); setSuccess(value); setError(''); focusCard(value.month);
  };
  const confirm = async () => {
    if (!closing || !data?.can_close || posting.current || busy || loading || forbiddenSession.current) return;
    const operation = {...closing,uncertain:true}, epoch = session.current;
    posting.current = true; setBusy(true); setClosing(operation); setError('');
    try {
      const result = await api.closeFinancePeriod(operation.year, operation.month, operation.reason);
      if (!mounted.current || epoch !== session.current) return;
      if (result.year !== operation.year || result.month !== operation.month || result.is_closed !== true) throw new Error('Invalid close response');
      closed(result);
    } catch (cause) {
      if (!mounted.current || epoch !== session.current) return;
      const status = (cause as {status?:number}).status;
      if ([401,403].includes(status || 0)) { forbidden(); return; }
      if (status === 400) { setClosing(null); setEditing(operation.month); setReason(operation.reason); setReasonError(true); setError(t.invalidReason); requestAnimationFrame(() => reasonField.current?.focus()); }
      else {
        setError(status === 409 ? t.conflict : t.unknown);
        const latest = await load();
        if (!mounted.current || epoch !== session.current) return;
        const actual = latest?.items.find(item => item.month === operation.month);
        if (actual?.is_closed) closed(actual);
        else if (latest?.can_close !== false) setError(t.unknown);
      }
    } finally { posting.current = false; if (mounted.current && epoch === session.current) setBusy(false); }
  };
  const changeYear = (event: React.FormEvent) => {
    event.preventDefault(); if (busy || closing) return;
    if (!validYear(yearInput)) { setYearError(true); setError(t.invalidYear); return; }
    setYearError(false); setError(''); setData(null); setEditing(null); setReason(''); setSuccess(null); generation.current++;
    const next = Number(yearInput); if (next === year) void load(); else setYear(next);
  };
  const check = (event: React.FormEvent) => {
    event.preventDefault(); if (!data?.can_close || editing === null || loading || busy) return;
    if (!reason.trim() || reason.length > 4000 || reason.includes('\0')) { setReasonError(true); setError(t.invalidReason); reasonField.current?.focus(); return; }
    setReasonError(false); setError(''); setClosing({year,month:editing,reason:reason.trim(),uncertain:false}); requestAnimationFrame(() => summary.current?.focus());
  };
  const locked = busy || !!closing;
  return <section className="min-w-0 space-y-4 rounded-xl border border-slate-300 bg-white p-4 text-slate-950 dark:border-slate-600 dark:bg-slate-900 dark:text-slate-100" aria-labelledby={`${prefix}-title`} aria-busy={loading||busy}>
    <div className="flex flex-wrap items-start justify-between gap-3"><h2 id={`${prefix}-title`} ref={title} tabIndex={-1} className="text-xl font-bold focus-visible:outline-2 focus-visible:outline-blue-600">{t.title}</h2><button type="button" className={button} disabled={loading||locked||denied} onClick={() => {setError('');void load();}}>{t.refresh}</button></div>
    <p className="text-sm text-slate-600 dark:text-slate-300">{t.help}</p><p className="text-sm text-slate-600 dark:text-slate-300">{t.dates}</p>
    <form onSubmit={changeYear} className="flex min-w-0 flex-wrap items-end gap-2" noValidate><label htmlFor={`${prefix}-year`} className="min-w-0 text-sm">{t.year}<input id={`${prefix}-year`} type="text" inputMode="numeric" maxLength={4} value={yearInput} disabled={loading||locked||denied} aria-invalid={yearError||undefined} aria-describedby={yearError?`${prefix}-error`:undefined} onChange={event => {setYearInput(event.target.value);setYearError(false);}} className={`${input} sm:max-w-40`}/></label><button type="submit" className={button} disabled={loading||locked||denied}>{t.show}</button></form>
    {error&&<p id={`${prefix}-error`} role="alert" className="break-words text-sm text-rose-800 dark:text-rose-200">{error}</p>}
    {loading&&<p role="status">{t.loading}</p>}
    {success&&<p role="status" className="break-words text-sm font-semibold text-emerald-800 dark:text-emerald-200">{t.closedSuccess}: {monthLabel(success)}</p>}
    {!loading&&!data&&!denied&&<button type="button" className={button} disabled={busy} onClick={() => {setError('');void load();}}>{t.retry}</button>}
    {closing&&<fieldset tabIndex={-1} ref={summary} className="min-w-0 space-y-3 rounded-lg border border-blue-700 p-3 focus-visible:outline-2 focus-visible:outline-blue-600 dark:border-blue-400"><legend className="px-1 font-semibold">{t.summary}</legend><h3 className="font-semibold">{monthLabel(closing)}</h3><p className="whitespace-pre-wrap break-words text-sm">{closing.reason}</p><p className="text-sm text-amber-900 dark:text-amber-200">{t.warning}</p>{closing.uncertain&&<p className="text-sm text-amber-900 dark:text-amber-200">{t.unknown}</p>}<div className="flex flex-wrap gap-2"><button type="button" className={primary} disabled={loading||busy||!data?.can_close} onClick={() => void confirm()}>{busy?t.saving:closing.uncertain?t.retryClose:t.confirm}</button>{!closing.uncertain&&<button type="button" className={button} onClick={() => {setClosing(null);requestAnimationFrame(() => reasonField.current?.focus());}}>{t.edit}</button>}</div></fieldset>}
    {data&&<>{!data.can_close&&<p className="text-sm">{t.readOnly}</p>}<div className="grid min-w-0 gap-3 sm:grid-cols-2 lg:grid-cols-3">{data.items.map(period=><article key={period.month} className="min-w-0 space-y-3 rounded-lg border border-slate-300 p-3 dark:border-slate-600"><h3 id={`${prefix}-month-${period.month}`} tabIndex={-1} className="font-semibold focus-visible:outline-2 focus-visible:outline-blue-600">{monthLabel(period)}</h3><p className={period.is_closed?'text-sm font-semibold text-emerald-800 dark:text-emerald-200':'text-sm text-slate-600 dark:text-slate-300'}>{period.is_closed?t.closed:t.open}</p>{period.is_closed?<dl className="space-y-2 text-sm">{[[t.author,period.closed_by_name||'—'],[t.time,timestamp(period.closed_at)],[t.reason,period.close_reason||'—']].map(([label,value])=><div key={label} className="min-w-0"><dt className="text-slate-600 dark:text-slate-300">{label}</dt><dd className="whitespace-pre-wrap break-words">{value}</dd></div>)}</dl>:data.can_close&&<><button id={`${prefix}-close-${period.month}`} type="button" className={button} aria-expanded={editing===period.month} aria-controls={`${prefix}-form-${period.month}`} disabled={loading||locked} onClick={() => {setEditing(period.month);setReason('');setError('');setReasonError(false);setSuccess(null);requestAnimationFrame(() => reasonField.current?.focus());}}>{t.close}</button><div id={`${prefix}-form-${period.month}`}>{editing===period.month&&!closing&&<form onSubmit={check} className="min-w-0 space-y-3" noValidate><label htmlFor={`${prefix}-reason`} className="block text-sm">{t.reason}</label><textarea id={`${prefix}-reason`} ref={reasonField} maxLength={4000} required disabled={loading||busy} value={reason} onChange={event => {setReason(event.target.value);setReasonError(false);setError('');}} aria-invalid={reasonError||undefined} aria-describedby={reasonError?`${prefix}-error`:undefined} className={input}/><div className="flex flex-wrap gap-2"><button type="submit" className={primary} disabled={loading||busy}>{t.check}</button><button type="button" className={button} onClick={() => {setEditing(null);setReason('');setError('');document.getElementById(`${prefix}-close-${period.month}`)?.focus();}}>{t.cancel}</button></div></form>}</div></>}</article>)}</div></>}
  </section>;
}
