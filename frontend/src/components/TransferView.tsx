'use client';

import { FormEvent, useCallback, useEffect, useRef, useState } from 'react';
import { api } from '@/lib/api';
import { transferTranslations } from '@/lib/transfer-i18n';
import type { LanguageCode, StockTransfer, TransferCatalog, TransferInput, TransferStatus, WarehouseNames } from '@/types';

const base = 'min-h-11 rounded-lg px-4 py-2 text-sm font-semibold focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600 disabled:opacity-50';
const button = `${base} border border-slate-300 hover:bg-slate-100 dark:border-slate-600 dark:hover:bg-slate-800`;
const primary = `${base} bg-blue-700 text-white hover:bg-blue-800 dark:bg-blue-700 dark:hover:bg-blue-800`;
const control = 'mt-1 min-h-11 w-full min-w-0 rounded-lg border border-slate-300 bg-white px-3 py-2 text-slate-950 dark:border-slate-600 dark:bg-slate-950 dark:text-slate-100 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600';
const panel = 'min-w-0 space-y-4 rounded-xl border border-slate-300 bg-white p-4 dark:border-slate-600 dark:bg-slate-900';
const statuses: TransferStatus[] = ['draft', 'pending_approval', 'approved', 'in_transit', 'received', 'rejected', 'cancelled'];
const emptyCatalog: TransferCatalog = { sources: [], destinations: [], skus: [], stock: [], permissions: [] };
type DraftLine = { key: number; skuId: string; qty: string; sourceLocation: string; destinationLocation: string; batch: string; expiry: string };
type Confirmation = 'dispatch' | 'receive' | 'cancel';

export function TransferView({ lang, warehouseId, initialTransferId, onBusyChange }: { lang: LanguageCode; warehouseId: number; initialTransferId?: number; onBusyChange: (busy: boolean) => void }) {
  const t = transferTranslations[lang];
  const [catalog, setCatalog] = useState<TransferCatalog>(emptyCatalog), [items, setItems] = useState<StockTransfer[]>([]);
  const [selected, setSelected] = useState<StockTransfer | null>(null), [editing, setEditing] = useState<number | null | false>(false);
  const [loading, setLoading] = useState(true), [saving, setSaving] = useState(false), [offset, setOffset] = useState(0), [count, setCount] = useState(0);
  const [status, setStatus] = useState<TransferStatus | ''>(''), [error, setError] = useState(''), [notice, setNotice] = useState(''), [invalid, setInvalid] = useState(false);
  const [number, setNumber] = useState(''), [sourceId, setSourceId] = useState(''), [destinationId, setDestinationId] = useState(''), [comment, setComment] = useState('');
  const [reason, setReason] = useState(''), [reasonInvalid, setReasonInvalid] = useState(false), [confirmation, setConfirmation] = useState<Confirmation | null>(null);
  const [lines, setLines] = useState<DraftLine[]>([]);
  const openedInitial = useRef<number | undefined>(undefined), intendedDetail = useRef<number | null>(null);
  const mounted = useRef(true), listRequest = useRef(0), catalogRequest = useRef(0), detailRequest = useRef(0), lineKey = useRef(0), busyLock = useRef(false);
  const heading = useRef<HTMLHeadingElement>(null), detailsHeading = useRef<HTMLHeadingElement>(null), formHeading = useRef<HTMLHeadingElement>(null), confirmHeading = useRef<HTMLHeadingElement>(null), addButton = useRef<HTMLButtonElement>(null), origin = useRef<HTMLButtonElement | null>(null);
  const locale = { ru:'ru-RU', ky:'ky-KG', 'zh-Hans':'zh-CN', 'zh-Hant':'zh-TW' }[lang];
  const name = (value: WarehouseNames) => (lang === 'ky' ? value.name_ky : lang.startsWith('zh') ? value.name_zh : value.name_ru) || value.name_ru || value.name_ky || value.name_zh || t.unknown;
  const warehouseName = (item: StockTransfer, side: 'source' | 'destination') => name({ name_ru:item[`${side}_name_ru`], name_ky:item[`${side}_name_ky`], name_zh:item[`${side}_name_zh`] });
  const amount = (value: string | number) => new Intl.NumberFormat(locale, { maximumFractionDigits:3 }).format(Number(value));
  const expiryDate = (value: string) => new Intl.DateTimeFormat(locale, { dateStyle:'medium' }).format(new Date(`${value}T00:00:00`));
  const date = (value: string | null) => value ? new Intl.DateTimeFormat(locale, { dateStyle:'medium', timeStyle:'short' }).format(new Date(value)) : t.pending;
  const canCreate = catalog.permissions.includes('warehouse.transfer.manage') && catalog.sources.length > 0;
  const source = catalog.sources.find(x => String(x.id) === sourceId), destination = catalog.destinations.find(x => String(x.id) === destinationId);
  const makeLine = (): DraftLine => ({ key:lineKey.current++, skuId:'', qty:'', sourceLocation:'', destinationLocation:'', batch:'', expiry:'' });
  const stockFor = (line: DraftLine) => catalog.stock.find(x => x.warehouse_id === Number(sourceId) && x.sku_id === Number(line.skuId) && x.location_id === (line.sourceLocation ? Number(line.sourceLocation) : null));
  const available = (line: DraftLine) => { const stock = stockFor(line); return line.batch ? stock?.batches.find(b => b.batch_no === line.batch && b.expiry_date === line.expiry)?.qty || '0' : stock?.unbatched_qty || '0'; };
  const errorText = useCallback((cause: unknown) => {
    const e = cause as { status?: number; code?: string };
    if (e.code === 'insufficient_stock') return t.insufficient;
    if (e.code === 'batch_required') return t.batchRequired;
    if (e.code === 'batch_conflict') return t.batchConflict;
    if (e.code === 'legacy_endpoint_retired') return t.retired;
    if (e.status === 401 || e.status === 403) return t.forbidden;
    if (e.status === 409) return t.conflict;
    if (e.status === 400) return t.invalid;
    return t.failed;
  }, [t]);
  const clearAccess = useCallback(() => { listRequest.current++; catalogRequest.current++; detailRequest.current++; intendedDetail.current = null; setLoading(false); setCatalog(emptyCatalog); setItems([]); setSelected(null); setEditing(false); setConfirmation(null); setCount(0); }, []);
  const loadCatalog = useCallback(async () => {
    const id = ++catalogRequest.current;
    try { const result = await api.getTransferCatalog(); if (mounted.current && id === catalogRequest.current) setCatalog(result); }
    catch (cause) { if (mounted.current && id === catalogRequest.current) { if ([401,403].includes((cause as {status?:number}).status || 0)) clearAccess(); setError(errorText(cause)); } }
  }, [clearAccess, errorText]);
  const loadList = useCallback(async () => {
    const id = ++listRequest.current; setLoading(true);
    try { const result = await api.getTransfers({ warehouse_id:warehouseId, offset, limit:20, status:status || undefined }); if (mounted.current && id === listRequest.current) { setItems(result.items); setCount(result.count); } }
    catch (cause) { if (mounted.current && id === listRequest.current) { setItems([]); setSelected(null); setCount(0); if ([401,403].includes((cause as {status?:number}).status || 0)) clearAccess(); setError(errorText(cause)); } }
    finally { if (mounted.current && id === listRequest.current) setLoading(false); }
  }, [warehouseId, offset, status, clearAccess, errorText]);
  const loadDocument = useCallback(async (id: number) => {
    intendedDetail.current = id;
    const request = ++detailRequest.current;
    try {
      const result = await api.getTransfers({ id, limit:1 });
      if (mounted.current && request === detailRequest.current) { setSelected(result.items[0] || null); if (!result.items.length) throw new Error('missing'); }
    } catch (cause) {
      if (!mounted.current || request !== detailRequest.current) return;
      setSelected(null);
      if ([401,403].includes((cause as {status?:number}).status || 0)) { clearAccess(); await loadCatalog(); }
      throw cause;
    }
  }, [clearAccess, loadCatalog]);
  useEffect(() => { mounted.current = true; return () => { mounted.current = false; onBusyChange(false); }; }, [onBusyChange]);
  useEffect(() => { onBusyChange(saving); }, [saving, onBusyChange]);
  useEffect(() => { void loadCatalog(); }, [loadCatalog]);
  useEffect(() => { void loadList(); }, [loadList]);
  useEffect(() => { if (initialTransferId && openedInitial.current !== initialTransferId) { openedInitial.current = initialTransferId; void loadDocument(initialTransferId).catch(cause => { if (mounted.current) setError(errorText(cause)); }); } }, [initialTransferId, loadDocument, errorText]);
  useEffect(() => { if (selected?.id) detailsHeading.current?.focus(); }, [selected?.id]);
  useEffect(() => { if (editing !== false) formHeading.current?.focus(); }, [editing]);
  useEffect(() => { if (confirmation) confirmHeading.current?.focus(); }, [confirmation]);
  const open = async (id: number, trigger?: HTMLButtonElement) => {
    if (trigger) origin.current = trigger;
    setSelected(null); setError(''); setReason(''); setReasonInvalid(false); setConfirmation(null); setEditing(false);
    try { await loadDocument(id); } catch (cause) { if (mounted.current) setError(errorText(cause)); }
  };
  const refresh = async () => { const id = selected?.id || intendedDetail.current; setError(''); setSelected(old => old ? {...old,allowed_actions:[]} : null); await Promise.all([loadList(),loadCatalog()]); if (id && intendedDetail.current === id) try { await loadDocument(id); } catch (cause) { setError(errorText(cause)); } };
  const run = async (work: () => Promise<{id:number}>, closeForm = false) => {
    if (busyLock.current) return;
    busyLock.current = true; setSaving(true); setError(''); setNotice(''); setReasonInvalid(false);
    try {
      const result = await work();
      if (!mounted.current) return;
      if (closeForm) setEditing(false);
      setConfirmation(null); setNotice(t.success);
      await Promise.all([loadList(),loadCatalog()]); await loadDocument(result.id);
    } catch (cause) {
      if (!mounted.current) return;
      const code = (cause as {status?:number}).status;
      if (code === 401 || code === 403) { clearAccess(); await loadCatalog(); }
      else if (code === 409) { await Promise.all([loadList(),loadCatalog()]); if (selected) try { await loadDocument(selected.id); } catch { setSelected(null); } setConfirmation(null); }
      setError(errorText(cause));
    } finally { busyLock.current = false; if (mounted.current) setSaving(false); }
  };
  const start = (item?: StockTransfer) => {
    detailRequest.current++; intendedDetail.current = null;
    setEditing(item?.id || null); setSelected(null); setConfirmation(null); setError(''); setInvalid(false);
    setNumber(item?.transfer_no || ''); setSourceId(String(item?.source_warehouse_id || catalog.sources.find(x => x.id === warehouseId)?.id || catalog.sources[0]?.id || ''));
    setDestinationId(item ? String(item.destination_warehouse_id) : ''); setComment(item?.comment || '');
    setLines(item ? item.items.map(row => ({key:lineKey.current++,skuId:String(row.sku_id),qty:String(row.qty),sourceLocation:row.source_location_id ? String(row.source_location_id) : '',destinationLocation:row.destination_location_id ? String(row.destination_location_id) : '',batch:row.batch_no,expiry:row.expiry_date || ''})) : [makeLine()]);
  };
  const submit = (event: FormEvent) => {
    event.preventDefault();
    const valid = number.trim() && sourceId && destinationId && sourceId !== destinationId && lines.length && new Set(lines.map(x => x.skuId)).size === lines.length && lines.every(line => line.skuId && /^\d+$/.test(line.qty) && Number(line.qty) > 0 && Number(line.qty) <= Number(available(line)) && Boolean(line.batch) === Boolean(line.expiry));
    if (!valid) { setInvalid(true); setError(t.invalid); return; }
    const data: TransferInput = { transfer_no:number.trim(), source_warehouse_id:Number(sourceId), destination_warehouse_id:Number(destinationId), comment, items:lines.map(line => ({sku_id:Number(line.skuId),qty:Number(line.qty),source_location_id:line.sourceLocation ? Number(line.sourceLocation) : undefined,destination_location_id:line.destinationLocation ? Number(line.destinationLocation) : undefined,batch_no:line.batch || undefined,expiry_date:line.expiry || undefined})) };
    void run(() => editing === null ? api.createTransfer(data) : api.updateTransfer(editing as number,data), true);
  };
  const decide = (decision: 'approve' | 'return' | 'reject') => {
    if (!selected) return;
    if (decision !== 'approve' && !reason.trim()) { setReasonInvalid(true); setError(t.reasonRequired); return; }
    void run(() => api.reviewTransfer(selected.id,decision,reason));
  };
  const updateLine = (key:number, patch:Partial<DraftLine>) => setLines(old => old.map(line => line.key === key ? {...line,...patch} : line));
  const errorProps = { 'aria-invalid':invalid, 'aria-describedby':invalid ? 'transfer-error' : undefined };
  const stageLabel = (action: string) => ({'warehouse.transfer_created':t.created,'warehouse.transfer_edited':t.edit,'warehouse.transfer_submit':t.submit,'warehouse.transfer_review_approve':t.approve,'warehouse.transfer_review_return':t.returned,'warehouse.transfer_review_reject':t.reject,'warehouse.transfer_dispatch':t.dispatch,'warehouse.transfer_receive':t.receive,'warehouse.transfer_cancel':t.cancel})[action] || t.details;
  return <section className="min-w-0 space-y-4" aria-labelledby="transfer-heading">
    <header className="flex flex-wrap items-start justify-between gap-3"><h2 id="transfer-heading" ref={heading} tabIndex={-1} className="text-xl font-bold focus-visible:outline-2 focus-visible:outline-blue-600">{t.title}</h2><div className="flex flex-wrap gap-2"><button className={button} disabled={saving || loading} onClick={() => void refresh()}>{t.refresh}</button>{canCreate && <button className={primary} disabled={saving} onClick={() => start()}>{t.create}</button>}</div></header>
    {error && <div className="rounded-lg border border-rose-300 bg-rose-50 p-3 text-rose-800 dark:border-rose-700 dark:bg-rose-950 dark:text-rose-200"><p id="transfer-error" role="alert">{error}</p><button className={`${button} mt-2`} disabled={saving} onClick={() => void refresh()}>{t.retry}</button></div>}
    <p role="status" className="text-sm text-emerald-800 dark:text-emerald-200">{notice}</p>
    <p className="text-sm text-slate-600 dark:text-slate-300">{t.transitHelp}</p>
    {!canCreate && catalog.permissions.includes('warehouse.transfer.manage') && <p>{t.noSource}</p>}
    <label className="block max-w-sm text-sm">{t.status}<select className={control} value={status} disabled={saving} onChange={e => {detailRequest.current++;intendedDetail.current=null;setStatus(e.target.value as TransferStatus | '');setOffset(0);setSelected(null);setConfirmation(null);setEditing(false);}}><option value="">{t.all}</option>{statuses.map(s => <option key={s} value={s}>{t[s]}</option>)}</select></label>
    {editing !== false && <form onSubmit={submit} className={panel}><h3 ref={formHeading} tabIndex={-1} className="text-lg font-semibold focus-visible:outline-2 focus-visible:outline-blue-600">{t.formTitle}</h3><fieldset disabled={saving} className="space-y-4"><div className="grid gap-3 sm:grid-cols-2">
      <label>{t.number}<input className={control} required maxLength={64} readOnly={editing !== null} value={number} onChange={e=>setNumber(e.target.value)} {...errorProps}/></label>
      <label>{t.source}<select className={control} required disabled={editing !== null} value={sourceId} onChange={e=>{setSourceId(e.target.value);if(e.target.value===destinationId)setDestinationId('');setLines([makeLine()]);}} {...errorProps}><option value="">—</option>{catalog.sources.map(w=><option key={w.id} value={w.id}>{name(w)}</option>)}</select></label>
      <label>{t.destination}<select className={control} required disabled={editing !== null} value={destinationId} onChange={e=>{setDestinationId(e.target.value);setLines(old=>old.map(line=>({...line,destinationLocation:''})));}} {...errorProps}><option value="">—</option>{catalog.destinations.filter(w=>String(w.id)!==sourceId).map(w=><option key={w.id} value={w.id}>{name(w)}</option>)}</select></label>
      <label>{t.comment}<textarea className={control} maxLength={4000} value={comment} onChange={e=>setComment(e.target.value)}/></label>
    </div><p className="text-sm text-slate-600 dark:text-slate-300">{t.lineHelp}</p>{lines.map((line,index)=>{const stock=stockFor(line);return <fieldset key={line.key} className="min-w-0 space-y-3 rounded-lg border border-slate-300 p-3 dark:border-slate-600"><legend className="px-1 font-medium">{t.line} {index+1}</legend><div className="grid gap-3 sm:grid-cols-2">
      <label>{t.sku}<select className={control} required value={line.skuId} onChange={e=>updateLine(line.key,{skuId:e.target.value,sourceLocation:'',destinationLocation:'',batch:'',expiry:''})} {...errorProps}><option value="">—</option>{catalog.skus.filter(sku=>!lines.some(other=>other.key!==line.key&&other.skuId===String(sku.id))).map(sku=><option key={sku.id} value={sku.id}>{sku.sku_code} · {name(sku)}</option>)}</select></label>
      <label>{t.qty}<input className={control} type="number" required min="1" max="2147483647" step="1" value={line.qty} onChange={e=>updateLine(line.key,{qty:e.target.value})} {...errorProps}/></label>
      <label>{t.sourceLocation}<select className={control} value={line.sourceLocation} onChange={e=>updateLine(line.key,{sourceLocation:e.target.value,batch:'',expiry:''})} {...errorProps}><option value="">{t.unlocated}</option>{source?.locations.map(loc=><option key={loc.id} value={loc.id}>{loc.code}</option>)}</select></label>
      <label>{t.destinationLocation}<select className={control} value={line.destinationLocation} onChange={e=>updateLine(line.key,{destinationLocation:e.target.value})}><option value="">{t.unlocated}</option>{destination?.locations.map(loc=><option key={loc.id} value={loc.id}>{loc.code}</option>)}</select></label>
      <label>{t.batch}<select className={control} value={line.batch} onChange={e=>{const batch=stock?.batches.find(b=>b.batch_no===e.target.value);updateLine(line.key,{batch:batch?.batch_no||'',expiry:batch?.expiry_date||''});}} {...errorProps}><option value="" disabled={!!stock?.batches.length&&Number(stock.unbatched_qty)<=0}>{t.noBatch}</option>{stock?.batches.map(batch=><option key={batch.batch_no} value={batch.batch_no}>{batch.batch_no} · {expiryDate(batch.expiry_date)} · {amount(batch.qty)}</option>)}{line.batch&&!stock?.batches.some(b=>b.batch_no===line.batch)&&<option value={line.batch} disabled>{line.batch} · {line.expiry ? expiryDate(line.expiry) : '—'} · 0</option>}</select></label>
    </div><p className="text-sm">{t.available}: {amount(available(line))}</p><p className="text-sm text-slate-600 dark:text-slate-300">{t.stockHelp}</p><button type="button" className={button} disabled={lines.length===1} aria-label={`${t.remove} ${index+1}`} onClick={()=>{setLines(old=>old.filter(x=>x.key!==line.key));addButton.current?.focus();}}>{t.remove}</button></fieldset>;})}<div className="flex flex-wrap gap-2"><button type="button" ref={addButton} className={button} disabled={lines.length>=100} onClick={()=>setLines(old=>[...old,makeLine()])}>{t.add}</button><button className={primary}>{saving?t.saving:t.save}</button><button type="button" className={button} onClick={()=>{setEditing(false);heading.current?.focus();}}>{t.cancelEdit}</button></div></fieldset></form>}
    <div aria-busy={loading}>{loading?<p role="status">{t.loading}</p>:!items.length?<p>{t.empty}</p>:<><div className="hidden overflow-x-auto sm:block"><table className="w-full text-left text-sm"><caption className="sr-only">{t.title}</caption><thead><tr>{[t.number,t.source,t.destination,t.status,t.date,t.inTransit,t.action].map(label=><th key={label} scope="col" className="border-b border-slate-300 p-3 dark:border-slate-600">{label}</th>)}</tr></thead><tbody>{items.map(item=><tr key={item.id} className="border-b border-slate-200 dark:border-slate-700"><td className="max-w-xs break-words p-3">{item.transfer_no}</td><td className="max-w-xs break-words p-3">{warehouseName(item,'source')}</td><td className="max-w-xs break-words p-3">{warehouseName(item,'destination')}</td><td className="p-3">{t[item.status]}</td><td className="p-3">{date(item.created_at)}</td><td className="p-3">{amount(item.in_transit_qty)}</td><td className="p-3"><button className={button} disabled={saving} onClick={e=>void open(item.id,e.currentTarget)}>{t.open}</button></td></tr>)}</tbody></table></div><div className="space-y-3 sm:hidden">{items.map(item=><article key={item.id} className={panel}><h3 className="break-words font-semibold">{item.transfer_no}</h3><dl className="grid grid-cols-2 gap-3 text-sm">{[[t.source,warehouseName(item,'source')],[t.destination,warehouseName(item,'destination')],[t.status,t[item.status]],[t.date,date(item.created_at)],[t.inTransit,amount(item.in_transit_qty)]].map(([key,value])=><div key={key} className="col-span-2 grid min-w-0 grid-cols-2 gap-3"><dt className="text-slate-600 dark:text-slate-300">{key}</dt><dd className="min-w-0 break-words">{value}</dd></div>)}</dl><button className={button} disabled={saving} onClick={e=>void open(item.id,e.currentTarget)}>{t.open}</button></article>)}</div></>}</div>
    {count>0&&<div className="flex flex-wrap items-center gap-3"><button className={button} disabled={saving||loading||offset===0} onClick={()=>{detailRequest.current++;intendedDetail.current=null;setOffset(Math.max(0,offset-20));setSelected(null);setEditing(false);}}>{t.previous}</button><span>{offset+1}–{offset+items.length} {t.of} {count}</span><button className={button} disabled={saving||loading||offset+items.length>=count} onClick={()=>{detailRequest.current++;intendedDetail.current=null;setOffset(offset+20);setSelected(null);setEditing(false);}}>{t.next}</button></div>}
    {selected&&<section aria-labelledby="transfer-details" className={panel}><div className="flex flex-wrap items-start justify-between gap-3"><h3 id="transfer-details" tabIndex={-1} ref={detailsHeading} className="min-w-0 break-words text-lg font-semibold focus-visible:outline-2 focus-visible:outline-blue-600">{t.details}: {selected.transfer_no}</h3><button className={button} disabled={saving} onClick={()=>{detailRequest.current++;intendedDetail.current=null;setSelected(null);setConfirmation(null);if(origin.current?.isConnected)origin.current.focus();else heading.current?.focus();}}>{t.close}</button></div><p className="break-words">{warehouseName(selected,'source')} → {warehouseName(selected,'destination')}</p><p>{t.status}: {t[selected.status]}</p><p>{t.inTransit}: {amount(selected.in_transit_qty)}</p><p className="break-words whitespace-pre-wrap">{selected.comment}</p>
      <ol aria-label={t.progress} className="grid gap-3 text-sm sm:grid-cols-4">{[[t.created,selected.created_at,selected.created_by_name],[t.approval,selected.approved_at,selected.approved_by_name],[t.dispatch,selected.dispatched_at,selected.dispatched_by_name],[t.receive,selected.received_at,selected.received_by_name]].map(([label,time,actor])=><li key={label} className="rounded-lg border border-slate-300 p-3 dark:border-slate-600"><p className="font-semibold">{label}</p><p>{actor||t.pending}</p><p>{date(time||null)}</p></li>)}</ol>
      <ul className="space-y-3">{selected.items.map(line=><li key={line.id} className="min-w-0 rounded-lg border border-slate-300 p-3 dark:border-slate-600"><p className="break-words font-medium">{line.sku_code} · {name(line)}</p><dl className="mt-2 grid gap-3 text-sm sm:grid-cols-2">{[[t.qty,amount(line.qty)],[t.sourceLocation,line.source_location_code||t.unlocated],[t.destinationLocation,line.destination_location_code||t.unlocated],[t.batch,line.batch_no||t.noBatch],[t.expiry,line.expiry_date?expiryDate(line.expiry_date):'—'],[t.inTransit,amount(line.in_transit_qty)],...(line.unit_cost!==undefined?[[t.cost,amount(line.unit_cost)]]:[])].map(([label,value])=><div key={label} className="grid min-w-0 grid-cols-2 gap-3"><dt className="text-slate-600 dark:text-slate-300">{label}</dt><dd className="min-w-0 break-words">{value}</dd></div>)}</dl></li>)}</ul>
      {selected.allowed_actions.includes('edit')&&<button className={button} disabled={saving} onClick={()=>start(selected)}>{t.edit}</button>}
      {selected.allowed_actions.includes('submit')&&<button className={primary} disabled={saving} onClick={()=>void run(()=>api.transferAction(selected.id,'submit'))}>{saving?t.saving:t.submit}</button>}
      {selected.allowed_actions.includes('review')&&<div className="space-y-3 border-t border-slate-300 pt-4 dark:border-slate-600"><h4 className="font-semibold">{t.review}</h4><label className="block">{t.reason}<textarea className={control} maxLength={4000} value={reason} aria-invalid={reasonInvalid} aria-describedby={reasonInvalid?'transfer-error':undefined} onChange={e=>setReason(e.target.value)}/></label><div className="flex flex-wrap gap-2"><button className={primary} disabled={saving} onClick={()=>decide('approve')}>{t.approve}</button><button className={button} disabled={saving} onClick={()=>decide('return')}>{t.return}</button><button className={button} disabled={saving} onClick={()=>decide('reject')}>{t.reject}</button></div></div>}
      <div className="flex flex-wrap gap-2">{(['dispatch','receive','cancel'] as const).filter(action=>selected.allowed_actions.includes(action)).map(action=><button key={action} className={action==='cancel'?button:primary} disabled={saving} onClick={()=>setConfirmation(action)}>{action==='dispatch'?t.send:action==='receive'?t.accept:t.cancel}</button>)}</div>
      {confirmation&&selected.allowed_actions.includes(confirmation)&&<div className="space-y-3 rounded-lg border border-amber-500 p-4"><h4 ref={confirmHeading} tabIndex={-1} className="font-semibold focus-visible:outline-2 focus-visible:outline-blue-600">{confirmation==='dispatch'?t.send:confirmation==='receive'?t.accept:t.cancel}</h4><p>{confirmation==='dispatch'?t.dispatchHelp:confirmation==='receive'?t.receiveHelp:t.cancelHelp}</p><p>{t.total}: {amount(selected.items.reduce((sum,line)=>sum+line.qty,0))}</p><div className="flex flex-wrap gap-2"><button className={primary} disabled={saving} onClick={()=>void run(()=>api.transferAction(selected.id,confirmation))}>{saving?t.saving:t.confirm}</button><button className={button} disabled={saving} onClick={()=>{setConfirmation(null);detailsHeading.current?.focus();}}>{t.back}</button></div></div>}
      <div className="space-y-3 border-t border-slate-300 pt-4 dark:border-slate-600"><h4 className="font-semibold">{t.history}</h4>{selected.review_comment&&<p className="break-words whitespace-pre-wrap">{selected.review_comment}</p>}{selected.history.length?<ol className="space-y-3">{selected.history.map(event=><li key={event.id} className="break-words text-sm"><p>{event.actor_name} · {date(event.created_at)} · {stageLabel(event.action)}</p>{event.comment&&<p className="whitespace-pre-wrap">{event.comment}</p>}</li>)}</ol>:<p>{t.noHistory}</p>}</div>
    </section>}
  </section>;
}
