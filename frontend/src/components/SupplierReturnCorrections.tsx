'use client';

import { useCallback, useEffect, useId, useRef, useState } from 'react';
import { api } from '@/lib/api';
import { supplierReturnCorrectionTranslations } from '@/lib/supplier-return-corrections-i18n';
import type { LanguageCode, SupplierReturnCorrection, SupplierReturnCorrectionInput, SupplierReturnCorrectionsResponse, SupplierReturnFinance } from '@/types';

const buttonBase = 'min-h-11 rounded-lg border px-3 py-2 text-sm font-semibold focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600 disabled:opacity-50';
const button = `${buttonBase} border-slate-300 hover:bg-slate-100 dark:border-slate-600 dark:hover:bg-slate-800`;
const primary = `${buttonBase} border-blue-700 bg-blue-700 text-white hover:bg-blue-800 dark:border-blue-500 dark:bg-blue-700 dark:hover:bg-blue-800`;
const input = 'min-h-11 min-w-0 w-full rounded-lg border border-slate-500 bg-white px-3 py-2 text-slate-950 dark:border-slate-400 dark:bg-slate-900 dark:text-slate-100 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600 disabled:opacity-60';
interface Pending { userId: number; token: string | null; payload: SupplierReturnCorrectionInput; before: string; uncertain: boolean }
// Memory only. Unresolved operations survive a card/queue remount, never a browser reload.
const unresolved = new Map<number, Pending>();
export function clearCorrectionSession(userId: number) {
  for (const [id, entry] of unresolved) if (entry.userId !== userId || entry.token !== api.getToken()) unresolved.delete(id);
}
function pendingFor(id: number, userId: number) {
  const entry = unresolved.get(id);
  return entry?.userId === userId && entry.token === api.getToken() ? entry : null;
}
function cents(value: string): bigint | null {
  if (!/^\d{1,14}(?:\.\d{1,2})?$/.test(value)) return null;
  const [whole, fraction = ''] = value.split('.');
  return BigInt(whole) * BigInt(100) + BigInt(fraction.padEnd(2, '0'));
}
function validDate(value: string) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value) || value.startsWith('0000')) return false;
  const parsed = new Date(`${value}T00:00:00Z`);
  return !Number.isNaN(parsed.getTime()) && parsed.toISOString().slice(0, 10) === value;
}
function decimal(value: bigint) { return `${value / BigInt(100)}.${String(value % BigInt(100)).padStart(2, '0')}`; }
const initialForm = () => ({ payable: '', amount: '', date: '', document: '', reason: '' });

export function SupplierReturnCorrections({ item, userId, lang, onDenied }: { item: SupplierReturnFinance; userId: number; lang: LanguageCode; onDenied: () => void }) {
  const t = supplierReturnCorrectionTranslations[lang];
  const prefix = useId();
  const [data, setData] = useState<SupplierReturnCorrectionsResponse | null>(null);
  const [loading, setLoading] = useState(true), [error, setError] = useState(''), [field, setField] = useState('');
  const [form, setForm] = useState(initialForm), [editing, setEditing] = useState(false), [snapshot, setSnapshot] = useState<Pending | null>(() => pendingFor(item.id, userId));
  const [busy, setBusy] = useState(false), [success, setSuccess] = useState<SupplierReturnCorrection | null>(null);
  const [historyOffset, setHistoryOffset] = useState(0), [payableOffset, setPayableOffset] = useState(0);
  const [search, setSearch] = useState(''), [query, setQuery] = useState('');
  const mounted = useRef(true), generation = useRef(0), posting = useRef(false), deniedCallback = useRef(onDenied);
  const heading = useRef<HTMLHeadingElement>(null), summary = useRef<HTMLFieldSetElement>(null), payableSelect = useRef<HTMLSelectElement>(null);
  useEffect(() => { deniedCallback.current = onDenied; }, [onDenied]);
  const locale = {ru:'ru-RU',ky:'ky-KG','zh-Hans':'zh-CN','zh-Hant':'zh-TW'}[lang];
  const money = (value: string) => {
    const parsed = cents(value);
    if (parsed === null) return value;
    const separator = new Intl.NumberFormat(locale).formatToParts(1.1).find(part => part.type === 'decimal')?.value || '.';
    return `${new Intl.NumberFormat(locale).format(parsed / BigInt(100))}${separator}${String(parsed % BigInt(100)).padStart(2, '0')}`;
  };
  const date = (value: string, time = false) => {
    const parsed = time ? new Date(value) : new Date(`${value}T12:00:00`);
    return Number.isNaN(parsed.getTime()) ? value : new Intl.DateTimeFormat(locale, time ? {dateStyle:'medium',timeStyle:'short'} : {dateStyle:'medium'}).format(parsed);
  };
  const forbidden = useCallback(() => {
    unresolved.delete(item.id); generation.current++; setData(null); setForm(initialForm()); setSnapshot(null); setSuccess(null); setEditing(false); setError(t.forbidden); setLoading(false); deniedCallback.current();
  }, [item.id, t.forbidden]);
  const load = useCallback(async (signal?: AbortSignal) => {
    const request = ++generation.current;
    setLoading(true);
    try {
      const result = await api.getSupplierReturnCorrections(item.id, {limit:20,offset:historyOffset,payable_limit:20,payable_offset:payableOffset,q:query || undefined}, signal);
      if (!mounted.current || request !== generation.current) return;
      setData(result);
      if (!result.can_confirm) { unresolved.delete(item.id); setSnapshot(null); setEditing(false); setForm(initialForm()); }
    } catch (cause) {
      if (!mounted.current || request !== generation.current || signal?.aborted) return;
      if ([401,403].includes((cause as {status?: number}).status || 0)) forbidden();
      else { setData(null); setError(t.failed); }
    } finally { if (mounted.current && request === generation.current) setLoading(false); }
  }, [item.id, historyOffset, payableOffset, query, forbidden, t.failed]);
  const invalidate = useCallback(() => { generation.current++; }, []);
  useEffect(() => { mounted.current = true; return () => { mounted.current = false; invalidate(); }; }, [invalidate]);
  useEffect(() => { const controller = new AbortController(); void load(controller.signal); return () => controller.abort(); }, [load]);
  useEffect(() => { if (snapshot) summary.current?.focus(); }, [snapshot]);
  const selected = data?.payables.find(row => String(row.id) === form.payable);
  const change = (name: keyof typeof form, value: string) => { setForm(current => ({...current,[name]:value})); setField(''); setError(''); };
  const check = (event: React.FormEvent) => {
    event.preventDefault();
    if (!data?.can_confirm || busy || loading || snapshot) return;
    const amount = cents(form.amount.trim().replace(',', '.'));
    const remaining = selected ? cents(selected.outstanding_amount) : null;
    const badField = !selected ? 'payable' : amount === null || amount <= BigInt(0) ? 'amount' : !validDate(form.date) ? 'date' : !form.document.trim() ? 'document' : !form.reason.trim() ? 'reason' : '';
    if (badField || remaining === null) { setField(badField || 'payable'); setError(t.invalid); requestAnimationFrame(() => document.getElementById(`${prefix}-${badField || 'payable'}`)?.focus()); return; }
    if (amount! > remaining) { setField('amount'); setError(t.exceeds); requestAnimationFrame(() => document.getElementById(`${prefix}-amount`)?.focus()); return; }
    const payload: SupplierReturnCorrectionInput = {request_id:crypto.randomUUID(),payable_id:selected!.id,amount:decimal(amount!),currency:selected!.currency,posting_date:form.date,document_no:form.document.trim(),reason:form.reason.trim()};
    setError(''); setSnapshot({userId,token:api.getToken(),payload,before:selected!.outstanding_amount,uncertain:false});
  };
  const confirm = async () => {
    if (!snapshot || !data?.can_confirm || posting.current || busy || loading) return;
    posting.current = true; setBusy(true); setError('');
    const operation = {...snapshot,uncertain:true};
    unresolved.set(item.id, operation); setSnapshot(operation);
    try {
      const result = await api.confirmSupplierReturnCorrection(item.id, operation.payload);
      const pending = unresolved.get(item.id);
      if (pending?.payload.request_id === operation.payload.request_id) unresolved.delete(item.id);
      if (!mounted.current) return;
      setSnapshot(null); setEditing(false); setForm(initialForm()); setSuccess(result); setHistoryOffset(0); setPayableOffset(0);
      // Use the response as immutable evidence even if the subsequent refresh fails.
      setData(current => current ? {...current, corrections:[result,...current.corrections.filter(row => row.id !== result.id)]} : current);
      await load(); requestAnimationFrame(() => heading.current?.focus());
    } catch (cause) {
      if (!mounted.current) return;
      const {status,code} = cause as {status?:number;code?:string};
      if ([401,403].includes(status || 0)) { forbidden(); return; }
      if (status && status >= 400 && status < 500) {
        unresolved.delete(item.id); setSnapshot(null); setEditing(true);
        setForm({payable:String(operation.payload.payable_id),amount:operation.payload.amount,date:operation.payload.posting_date,document:operation.payload.document_no,reason:operation.payload.reason});
        if (code === 'period_closed') { setError(t.closed); setField('date'); }
        else if (code === 'idempotency_conflict') setError(t.keyConflict);
        else if (code === 'insufficient_outstanding' || code === 'invalid_payable') setError(t.conflict);
        else setError(t.invalid);
        if (status === 409) await load();
      } else { setSnapshot(operation); setError(t.unknown); await load(); }
    } finally { posting.current = false; if (mounted.current) setBusy(false); }
  };
  const pageButtons = (which: 'history' | 'payables', count: number, offset: number, length: number) => <div className="flex flex-wrap items-center gap-2 text-sm"><button type="button" className={button} disabled={loading||busy||!!snapshot||offset===0} onClick={() => {if(which==='history')setHistoryOffset(Math.max(0,offset-20));else {setPayableOffset(Math.max(0,offset-20));change('payable','');}}}>{t.previous}</button><span>{count ? offset+1 : 0}–{offset+length} {t.of} {count}</span><button type="button" className={button} disabled={loading||busy||!!snapshot||offset+length>=count} onClick={() => {if(which==='history')setHistoryOffset(offset+20);else {setPayableOffset(offset+20);change('payable','');}}}>{t.next}</button></div>;
  const errorId = `${prefix}-error`;
  const fieldProps = (name: string) => ({id:`${prefix}-${name}`,'aria-invalid':field===name || undefined,'aria-describedby':field===name ? errorId : undefined});
  const result = success;
  return <section aria-labelledby={`${prefix}-heading`} aria-busy={loading||busy} className="min-w-0 space-y-4 border-t border-slate-300 pt-4 dark:border-slate-600">
    <div className="flex flex-wrap items-center justify-between gap-2"><h4 id={`${prefix}-heading`} ref={heading} tabIndex={-1} className="font-semibold focus-visible:outline-2 focus-visible:outline-blue-600">{t.title}</h4><button type="button" className={button} disabled={loading||busy||!!snapshot} onClick={() => {setError('');void load();}}>{t.refresh}</button></div>
    <p className="text-sm text-slate-600 dark:text-slate-300">{t.help}</p>
    {error&&<p id={errorId} role="alert" className="break-words text-sm text-rose-800 dark:text-rose-200">{error}</p>}
    {loading&&<p role="status">{t.loading}</p>}
    {!loading&&!data&&<button type="button" className={button} onClick={() => {setError('');void load();}}>{t.retry}</button>}
    {result&&<div role="status" className="rounded-lg border border-green-700 p-3 text-sm dark:border-green-400"><strong>{t.posted}: {result.document_no}</strong><p>{money(result.amount)} {result.currency} · {t.after}: {money(result.outstanding_after)} {result.currency}</p>{cents(result.outstanding_after)===BigInt(0)&&<p>{t.settled}</p>}</div>}
    {data&&<>
      {!data.can_confirm&&<p className="text-sm">{t.noWrite}</p>}
      {data.can_confirm&&!editing&&!snapshot&&<button type="button" className={primary} disabled={loading||busy} onClick={() => {setEditing(true);setError('');setSuccess(null);requestAnimationFrame(()=>payableSelect.current?.focus());}}>{t.add}</button>}
      {editing&&!snapshot&&data.can_confirm&&<form onSubmit={check} className="min-w-0 space-y-3" aria-label={t.add} noValidate>
        <fieldset disabled={loading||busy} className="min-w-0 space-y-3"><legend className="font-semibold">{t.candidates}</legend>
          <div className="flex min-w-0 flex-wrap items-end gap-2"><label className="min-w-0 flex-1 text-sm" htmlFor={`${prefix}-search`}>{t.search}<input id={`${prefix}-search`} value={search} maxLength={128} onChange={event=>setSearch(event.target.value)} className={input}/></label><button type="button" className={button} onClick={()=>{setPayableOffset(0);setQuery(search.trim());change('payable','');}}>{t.searchButton}</button></div>
          {!data.payables.length&&<p className="text-sm">{t.noPayables}</p>}
          <div className="min-w-0 text-sm"><label className="block" htmlFor={`${prefix}-payable`}>{t.payable}</label><select {...fieldProps('payable')} ref={payableSelect} value={form.payable} onChange={event=>change('payable',event.target.value)} className={input} required><option value="">{t.choose}</option>{data.payables.map(row=><option key={row.id} value={row.id}>#{row.id} · {t.statement} #{row.source_id} · {t.original}: {money(row.amount)} · {t.remaining}: {money(row.outstanding_amount)} {row.currency}</option>)}</select></div>
          {pageButtons('payables',data.payable_count,payableOffset,data.payables.length)}
          <div className="grid min-w-0 gap-3 sm:grid-cols-2"><label className="min-w-0 text-sm" htmlFor={`${prefix}-amount`}>{t.amount}{selected?` (${selected.currency})`:''}<input {...fieldProps('amount')} inputMode="decimal" value={form.amount} maxLength={18} onChange={event=>change('amount',event.target.value)} className={input} required/></label><label className="min-w-0 text-sm" htmlFor={`${prefix}-date`}>{t.date}<input {...fieldProps('date')} type="date" value={form.date} onChange={event=>change('date',event.target.value)} className={input} required/></label><label className="min-w-0 text-sm sm:col-span-2" htmlFor={`${prefix}-document`}>{t.document}<input {...fieldProps('document')} value={form.document} maxLength={128} onChange={event=>change('document',event.target.value)} className={input} required/></label><label className="min-w-0 text-sm sm:col-span-2" htmlFor={`${prefix}-reason`}>{t.reason}<textarea {...fieldProps('reason')} value={form.reason} maxLength={4000} onChange={event=>change('reason',event.target.value)} className={input} required/></label></div>
          <div className="flex flex-wrap gap-2"><button type="submit" className={primary}>{t.check}</button><button type="button" className={button} onClick={()=>{setEditing(false);setError('');heading.current?.focus();}}>{t.cancel}</button></div>
        </fieldset>
      </form>}
      {snapshot&&data.can_confirm&&<fieldset ref={summary} tabIndex={-1} className="min-w-0 space-y-3 rounded-lg border border-blue-700 p-3 focus-visible:outline-2 focus-visible:outline-blue-600 dark:border-blue-400"><legend className="px-1 font-semibold">{t.summary}</legend><dl className="grid min-w-0 gap-3 text-sm sm:grid-cols-2">{[[t.returnNo,item.return_no],[t.payable,`#${snapshot.payload.payable_id}`],[t.before,`${money(snapshot.before)} ${snapshot.payload.currency}`],[t.amount,`${money(snapshot.payload.amount)} ${snapshot.payload.currency}`],[t.after,`${money(decimal((cents(snapshot.before)||BigInt(0))-(cents(snapshot.payload.amount)||BigInt(0))))} ${snapshot.payload.currency}`],[t.date,date(snapshot.payload.posting_date)],[t.document,snapshot.payload.document_no],[t.reason,snapshot.payload.reason]].map(([label,value])=><div key={label} className="min-w-0"><dt className="text-slate-600 dark:text-slate-300">{label}</dt><dd className="whitespace-pre-wrap break-words">{value}</dd></div>)}</dl><p className="text-sm text-amber-900 dark:text-amber-200">{t.warning}</p>{snapshot.uncertain&&<p className="text-sm text-amber-900 dark:text-amber-200">{t.unknown}</p>}<div className="flex flex-wrap gap-2"><button type="button" className={primary} disabled={loading||busy} onClick={()=>void confirm()}>{busy?t.saving:snapshot.uncertain?t.retry:t.confirm}</button>{!snapshot.uncertain&&<button type="button" className={button} disabled={busy} onClick={()=>{setSnapshot(null);setEditing(true);requestAnimationFrame(()=>payableSelect.current?.focus());}}>{t.edit}</button>}</div></fieldset>}
      <div className="min-w-0 space-y-3" aria-label={t.history}><h5 className="font-semibold">{t.history}</h5>{!data.corrections.length?<p className="text-sm">{t.empty}</p>:data.corrections.map(row=><article key={row.id} className="min-w-0 space-y-2 rounded-lg border border-slate-300 p-3 text-sm dark:border-slate-600"><h6 className="break-words font-semibold">{row.document_no}</h6><dl className="grid min-w-0 gap-2 sm:grid-cols-2">{[[t.date,date(row.posting_date)],[t.payable,`#${row.payable_id}`],[t.amount,`${money(row.amount)} ${row.currency}`],[t.before,`${money(row.outstanding_before)} ${row.currency}`],[t.after,`${money(row.outstanding_after)} ${row.currency}`],[t.author,row.confirmed_by_name],[t.confirmedAt,date(row.confirmed_at,true)],[t.reason,row.reason]].map(([label,value])=><div key={label} className="min-w-0"><dt className="text-slate-600 dark:text-slate-300">{label}</dt><dd className="whitespace-pre-wrap break-words">{value}</dd></div>)}</dl>{cents(row.outstanding_after)===BigInt(0)&&<p>{t.settled}</p>}</article>)}{data.correction_count>0&&pageButtons('history',data.correction_count,historyOffset,data.corrections.length)}</div>
    </>}
  </section>;
}
