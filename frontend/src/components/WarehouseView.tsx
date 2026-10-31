'use client';

import { FormEvent, ReactNode, useCallback, useEffect, useRef, useState } from 'react';
import { api } from '@/lib/api';
import { warehouseTranslations } from '@/lib/warehouse-i18n';
import { transferTranslations } from '@/lib/transfer-i18n';
import { TransferView } from './TransferView';
import { WriteoffView } from './WriteoffView';
import { writeoffTranslations } from '@/lib/writeoff-i18n';
import type { LanguageCode, User, WarehouseCatalog, WarehouseCount, WarehouseExpiry, WarehouseInventory, WarehouseMovement, WarehouseNames, WarehouseReceipt } from '@/types';

type View = 'inventory' | 'movements' | 'receipts' | 'counts' | 'expiry' | 'transfers' | 'writeoffs';
const views: View[] = ['inventory', 'movements', 'receipts', 'counts', 'expiry', 'transfers', 'writeoffs'];
type Document = { kind: 'receipts'; item: WarehouseReceipt } | { kind: 'counts'; item: WarehouseCount };
type DraftLine = { key: number; itemId: string; qty: string; locationId: string; batch: string; expiry: string; reason: string };
const buttonBase = 'min-h-11 rounded-lg px-4 py-2 text-sm font-semibold focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600 disabled:opacity-50';
const button = `${buttonBase} border border-slate-300 hover:bg-slate-100 dark:border-slate-600 dark:hover:bg-slate-800`;
const primary = `${buttonBase} bg-blue-700 text-white hover:bg-blue-800 dark:bg-blue-700 dark:hover:bg-blue-800`;
const control = 'mt-1 min-h-11 w-full min-w-0 rounded-lg border border-slate-300 bg-white px-3 py-2 text-slate-950 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600 dark:border-slate-600 dark:bg-slate-950 dark:text-slate-100';
const panel = 'space-y-4 rounded-xl border border-slate-300 bg-white p-4 dark:border-slate-600 dark:bg-slate-900';
const localeFor = (lang: LanguageCode) => ({ ru: 'ru-RU', ky: 'ky-KG', 'zh-Hans': 'zh-CN', 'zh-Hant': 'zh-TW' })[lang];
const emptyCatalog: WarehouseCatalog = { warehouses: [], skus: [], purchase_orders: [], permissions: [] };

function DataTable({ caption, headers, rows }: { caption: string; headers: string[]; rows: Array<{ key: number; cells: ReactNode[] }> }) {
  return <><div className="hidden overflow-x-auto sm:block"><table className="w-full text-left text-sm"><caption className="sr-only">{caption}</caption><thead><tr>{headers.map((header, index) => <th key={index} scope="col" className="border-b border-slate-300 p-3 dark:border-slate-600">{header}</th>)}</tr></thead><tbody>{rows.map(row => <tr key={row.key} className="border-b border-slate-200 dark:border-slate-700">{row.cells.map((cell, index) => <td key={index} className="max-w-sm break-words p-3 align-top">{cell}</td>)}</tr>)}</tbody></table></div><div className="space-y-3 sm:hidden">{rows.map(row => <article key={row.key} className="rounded-lg border border-slate-300 p-4 dark:border-slate-600"><dl className="space-y-3">{row.cells.map((cell, index) => <div key={index} className="grid min-w-0 grid-cols-2 gap-3 text-sm"><dt className="break-words text-slate-600 dark:text-slate-300">{headers[index]}</dt><dd className="min-w-0 break-words">{cell}</dd></div>)}</dl></article>)}</div></>;
}

export function WarehouseView({ lang, currentUser }: { lang: LanguageCode; currentUser: User }) {
  const t = warehouseTranslations[lang];
  const initialAccess = currentUser.role === 'general_director' || (currentUser.system_permissions || []).some(p => p.startsWith('warehouse.'));
  const [catalog, setCatalog] = useState<WarehouseCatalog>(emptyCatalog);
  const [catalogLoading, setCatalogLoading] = useState(true), [loading, setLoading] = useState(false), [saving, setSaving] = useState(false);
  const [warehouseId, setWarehouseId] = useState(''), [view, setView] = useState<View>('inventory');
  const [writeoffBusy, setWriteoffBusy] = useState(false), [writeoffId, setWriteoffId] = useState<number | undefined>();
  const [transferBusy, setTransferBusy] = useState(false), [transferId, setTransferId] = useState<number | undefined>();
  const [inventory, setInventory] = useState<WarehouseInventory[]>([]), [movements, setMovements] = useState<WarehouseMovement[]>([]);
  const [receipts, setReceipts] = useState<WarehouseReceipt[]>([]), [counts, setCounts] = useState<WarehouseCount[]>([]);
  const [expiry, setExpiry] = useState<WarehouseExpiry | null>(null), [days, setDays] = useState('30');
  const [offset, setOffset] = useState(0), [total, setTotal] = useState(0);
  const [error, setError] = useState(''), [notice, setNotice] = useState(''), [invalid, setInvalid] = useState(false);
  const [document, setDocument] = useState<Document | null>(null);
  const [form, setForm] = useState<'receipts' | 'counts' | null>(null), [number, setNumber] = useState(''), [orderId, setOrderId] = useState(''), [comment, setComment] = useState('');
  const lineKey = useRef(1);
  const makeLine = (): DraftLine => ({ key: lineKey.current++, itemId: '', qty: '', locationId: '', batch: '', expiry: '', reason: '' });
  const [lines, setLines] = useState<DraftLine[]>([{ key: 0, itemId: '', qty: '', locationId: '', batch: '', expiry: '', reason: '' }]);
  const request = useRef(0), catalogRequest = useRef(0), mounted = useRef(true);
  const heading = useRef<HTMLHeadingElement>(null), detailsHeading = useRef<HTMLHeadingElement>(null), trigger = useRef<HTMLButtonElement | null>(null);
  const can = useCallback((permission: string) => catalog.permissions.includes(permission), [catalog.permissions]);
  const canView = useCallback((target: View) => can(target === 'writeoffs' ? 'warehouse.writeoff.read' : target === 'transfers' ? 'warehouse.transfer.read' : target === 'inventory' || target === 'movements' || target === 'expiry' ? 'warehouse.inventory.read' : target === 'receipts' ? 'warehouse.receipt.read' : 'warehouse.count.read'), [can]);
  const warehouse = catalog.warehouses.find(x => x.id === Number(warehouseId));
  const order = catalog.purchase_orders.find(x => x.id === Number(orderId));
  const name = (x: WarehouseNames) => (lang === 'ky' ? x.name_ky : lang.startsWith('zh') ? x.name_zh : x.name_ru) || x.name_ru || x.name_ky || x.name_zh || t.unknown;
  const formatNumber = (value: string | number) => new Intl.NumberFormat(localeFor(lang), { maximumFractionDigits: 3 }).format(Number(value));
  const formatDate = (value: string) => new Intl.DateTimeFormat(localeFor(lang), { dateStyle: 'medium' }).format(new Date(value));
  const status = (value: string) => ({ draft: t.draft, posted: t.posted, cancelled: t.cancelled, counted: t.counted, approved: t.approved })[value] || t.unknown;
  const kindLabel = (value: string) => ({ receipt: t.receipt, issue: t.issue, transfer_out: t.transfer_out, transfer_in: t.transfer_in, adjustment: t.adjustment })[value] || t.otherSource;
  const sourceLabel = (value: string) => ({ purchase_receipt: t.receiptSource, stock_count: t.countSource, stock_transfer: t.transferSource, stock_writeoff: writeoffTranslations[lang].details })[value] || t.otherSource;
  const errorText = useCallback((cause: unknown) => {
    const e = cause as { status?: number; code?: string };
    if (e.code === 'batch_adjustment_required') return t.batchRequired;
    return e.status === 401 || e.status === 403 ? t.forbidden : e.status === 409 || e.code === 'conflict' ? t.conflict : e.status === 400 || e.code === 'validation_error' ? t.validation : t.failed;
  }, [t]);
  const clearData = useCallback(() => { setInventory([]); setMovements([]); setReceipts([]); setCounts([]); setExpiry(null); setTotal(0); setDocument(null); }, []);
  const loadCatalog = useCallback(async () => {
    const id = ++catalogRequest.current;
    setCatalogLoading(true);
    try {
      const response = await api.getWarehouseCatalog();
      if (!mounted.current || id !== catalogRequest.current) return;
      setCatalog(response);
      setWarehouseId(old => response.warehouses.some(w => String(w.id) === old) ? old : String(response.warehouses[0]?.id || ''));
    } catch (cause) {
      if (mounted.current && id === catalogRequest.current) {
        setError(errorText(cause));
        if ([401,403].includes((cause as { status?: number }).status || 0)) { setCatalog(emptyCatalog); setWarehouseId(''); clearData(); setForm(null); }
      }
    } finally { if (mounted.current && id === catalogRequest.current) setCatalogLoading(false); }
  }, [errorText, clearData]);
  const load = useCallback(async () => {
    const id = ++request.current;
    if (view === 'transfers' || view === 'writeoffs' || !warehouseId || !canView(view)) { clearData(); setLoading(false); return; }
    setLoading(true);
    try {
      const query = { warehouse_id: Number(warehouseId), offset, limit: 20 };
      const response = view === 'inventory' ? await api.getWarehouseInventory(query) : view === 'movements' ? await api.getWarehouseMovements(query) : view === 'receipts' ? await api.getWarehouseReceipts(query) : view === 'counts' ? await api.getWarehouseCounts(query) : await api.getWarehouseExpiry(Number(warehouseId), Number(days));
      if (!mounted.current || id !== request.current) return;
      if (view === 'inventory') setInventory((response as { items: WarehouseInventory[] }).items);
      if (view === 'movements') setMovements((response as { items: WarehouseMovement[] }).items);
      if (view === 'receipts') {
        const items = (response as { items: WarehouseReceipt[] }).items; setReceipts(items);
        setDocument(old => old?.kind === 'receipts' ? items.some(x => x.id === old.item.id) ? { kind: 'receipts', item: items.find(x => x.id === old.item.id)! } : null : old);
      }
      if (view === 'counts') {
        const items = (response as { items: WarehouseCount[] }).items; setCounts(items);
        setDocument(old => old?.kind === 'counts' ? items.some(x => x.id === old.item.id) ? { kind: 'counts', item: items.find(x => x.id === old.item.id)! } : null : old);
      }
      if (view === 'expiry') setExpiry(response as WarehouseExpiry);
      setTotal('count' in response ? response.count : 0);
    } catch (cause) {
      if (!mounted.current || id !== request.current) return;
      clearData(); setError(errorText(cause));
      if ((cause as { status?: number }).status === 403) { setCatalog(emptyCatalog); setForm(null); }
    } finally { if (mounted.current && id === request.current) setLoading(false); }
  }, [warehouseId, view, offset, days, canView, clearData, errorText]);
  useEffect(() => { mounted.current = true; return () => { mounted.current = false; }; }, []);
  useEffect(() => { if (initialAccess) void loadCatalog(); else setCatalogLoading(false); }, [initialAccess, loadCatalog]);
  useEffect(() => { const first = views.find(target => canView(target)); if (first && !canView(view)) setView(first); }, [canView, view]);
  useEffect(() => { void load(); }, [load]);
  const documentId = document ? `${document.kind}-${document.item.id}` : '';
  useEffect(() => { if (documentId) detailsHeading.current?.focus(); }, [documentId]);
  const changeContext = (target: View) => { setTransferId(undefined); setWriteoffId(undefined); setView(target); setOffset(0); clearData(); setForm(null); setError(''); setNotice(''); };
  const showDocument = (kind: 'receipts' | 'counts', item: WarehouseReceipt | WarehouseCount, origin: HTMLButtonElement) => {
    trigger.current = origin; setForm(null); setDocument(kind === 'receipts' ? { kind, item: item as WarehouseReceipt } : { kind, item: item as WarehouseCount });
  };
  const sourceOpen = async (movement: WarehouseMovement, origin: HTMLButtonElement) => {
    if (movement.source_type === 'stock_writeoff') { changeContext('writeoffs'); setWriteoffId(movement.source_id); return; }
    if (movement.source_type === 'stock_transfer') { changeContext('transfers'); setTransferId(movement.source_id); return; }
    const kind = movement.source_type === 'purchase_receipt' ? 'receipts' : 'counts';
    setSaving(true); setError('');
    try {
      const result = kind === 'receipts' ? await api.getWarehouseReceipts({ warehouse_id: Number(warehouseId), id: movement.source_id, limit: 1 }) : await api.getWarehouseCounts({ warehouse_id: Number(warehouseId), id: movement.source_id, limit: 1 });
      if (!result.items[0]) { setError(t.failed); return; }
      showDocument(kind, result.items[0], origin);
    } catch (cause) { setError(errorText(cause)); if ((cause as { status?: number }).status === 403) { clearData(); await loadCatalog(); } }
    finally { setSaving(false); }
  };
  const refreshDocument = async () => {
    if (!document) return;
    const query = { warehouse_id: Number(warehouseId), id: document.item.id, limit: 1 };
    try {
      const result = document.kind === 'receipts' ? await api.getWarehouseReceipts(query) : await api.getWarehouseCounts(query);
      const item = result.items[0];
      setDocument(!item ? null : document.kind === 'receipts' ? { kind: 'receipts', item: item as WarehouseReceipt } : { kind: 'counts', item: item as WarehouseCount });
    } catch (cause) { setDocument(null); throw cause; }
  };
  const run = async (action: () => Promise<unknown>, closeForm = false) => {
    setSaving(true); setError(''); setNotice(''); setInvalid(false);
    try {
      await action(); if (closeForm) setForm(null); setNotice(t.success); await loadCatalog(); await load();
      await refreshDocument();
    }
    catch (cause) {
      const e = cause as { status?: number };
      if (e.status === 403) { clearData(); setForm(null); await loadCatalog(); await load(); }
      if (e.status === 409) {
        await loadCatalog(); await load();
        try { await refreshDocument(); } catch { setDocument(null); }
      }
      setError(errorText(cause));
    } finally { setSaving(false); }
  };
  const startForm = (kind: 'receipts' | 'counts') => { setForm(kind); setDocument(null); setNumber(''); setOrderId(''); setComment(''); setLines([makeLine()]); setInvalid(false); setError(''); };
  const submit = (event: FormEvent) => {
    event.preventDefault();
    const ids = lines.map(x => x.itemId);
    const valid = number.trim() && warehouseId && ids.every(Boolean) && new Set(ids).size === ids.length && lines.every(line => {
      if (form === 'counts') return /^\d+(\.\d{1,3})?$/.test(line.qty) && Number.isFinite(Number(line.qty)) && Number(line.qty) >= 0;
      const expected = order?.items.find(x => x.id === Number(line.itemId));
      return /^\d+$/.test(line.qty) && Number(line.qty) > 0 && !!expected && Number(line.qty) <= expected.ordered_qty - expected.received_qty && (Number(line.qty) === expected.ordered_qty - expected.received_qty || !!line.reason.trim()) && Boolean(line.batch.trim()) === Boolean(line.expiry);
    });
    if (!valid || (form === 'receipts' && !order)) { setInvalid(true); setError(t.localInvalid); return; }
    if (form === 'receipts') void run(() => api.createWarehouseReceipt({ receipt_no: number.trim(), warehouse_id: Number(warehouseId), purchase_order_id: Number(orderId), comment, items: lines.map(line => ({ po_item_id: Number(line.itemId), qty: Number(line.qty), location_id: line.locationId ? Number(line.locationId) : undefined, batch_no: line.batch.trim() || undefined, expiry_date: line.expiry || undefined, discrepancy_reason: line.reason })) }), true);
    if (form === 'counts') void run(() => api.createWarehouseCount({ count_no: number.trim(), warehouse_id: Number(warehouseId), items: lines.map(line => ({ sku_id: Number(line.itemId), actual_qty: line.qty, reason: line.reason })) }), true);
  };
  const updateLine = (key: number, field: keyof DraftLine, value: string) => setLines(old => old.map(line => line.key === key ? { ...line, [field]: value } : line));
  const errorProps = { 'aria-invalid': invalid, 'aria-describedby': invalid ? 'warehouse-error' : undefined };
  const rowCount = view === 'inventory' ? inventory.length : view === 'movements' ? movements.length : view === 'receipts' ? receipts.length : counts.length;
  const inventoryCost = inventory.some(x => x.avg_cost !== undefined), movementCost = movements.some(x => x.unit_cost !== undefined);
  if (!initialAccess) return <p role="alert" className="p-6">{t.forbidden}</p>;
  return <section className="mx-auto max-w-7xl min-w-0 space-y-5 p-4 pb-24 text-slate-950 dark:text-slate-100 sm:p-6 sm:pb-24">
    <header className="flex flex-wrap items-start justify-between gap-4"><div className="min-w-0"><h1 ref={heading} tabIndex={-1} className="text-2xl font-bold">{t.title}</h1><p className="mt-1 text-sm text-slate-600 dark:text-slate-300">{t.subtitle}</p></div><button className={button} disabled={saving || transferBusy || writeoffBusy || loading || catalogLoading || view === 'transfers' || view === 'writeoffs'} onClick={() => { setError(''); void loadCatalog(); void load(); }}>{t.refresh}</button></header>
    {error && <div className="rounded-lg border border-rose-300 bg-rose-50 p-3 text-rose-800 dark:border-rose-700 dark:bg-rose-950 dark:text-rose-200"><p id="warehouse-error" role="alert">{error}</p><button className={`${button} mt-2`} disabled={saving} onClick={() => { setError(''); void loadCatalog(); void load(); }}>{t.retry}</button></div>}
    <p role="status" className="text-sm text-emerald-800 dark:text-emerald-200">{notice}</p>
    {catalogLoading ? <p role="status">{t.loading}</p> : !catalog.warehouses.length ? <p>{t.noWarehouses}</p> : <>
      <label className="block max-w-lg text-sm font-medium">{t.warehouse}<select className={control} disabled={saving || transferBusy || writeoffBusy} value={warehouseId} onChange={e => { setTransferId(undefined); setWriteoffId(undefined); setWarehouseId(e.target.value); setOffset(0); clearData(); setForm(null); setError(''); setNotice(''); }}>{catalog.warehouses.map(w => <option key={w.id} value={w.id}>{name(w)}</option>)}</select></label>
      <div className="flex flex-wrap gap-2">{views.filter(canView).map(target => <button key={target} type="button" className={view === target ? primary : button} aria-pressed={view === target} disabled={saving || transferBusy || writeoffBusy} onClick={() => changeContext(target)}>{target === 'transfers' ? transferTranslations[lang].title : target === 'writeoffs' ? writeoffTranslations[lang].title : t[target]}</button>)}</div>
      {view === 'transfers' ? <TransferView key={warehouseId} lang={lang} warehouseId={Number(warehouseId)} initialTransferId={transferId} onBusyChange={setTransferBusy} /> : view === 'writeoffs' ? <WriteoffView key={warehouseId} lang={lang} warehouseId={Number(warehouseId)} initialWriteoffId={writeoffId} onBusyChange={setWriteoffBusy} /> : <>
      <div className="flex flex-wrap gap-2">{view === 'receipts' && can('warehouse.receipt.manage') && <button className={primary} disabled={saving} onClick={() => startForm('receipts')}>{t.newReceipt}</button>}{view === 'counts' && can('warehouse.count.manage') && <button className={primary} disabled={saving} onClick={() => startForm('counts')}>{t.newCount}</button>}</div>
      {form && <form onSubmit={submit} className={panel}>
        <h2 className="text-lg font-semibold">{form === 'receipts' ? t.newReceipt : t.newCount}</h2><p className="text-sm text-slate-600 dark:text-slate-300">{t.formHelp}</p>{form === 'counts' && <p className="text-sm text-amber-900 dark:text-amber-200">{t.countHelp}</p>}
        <fieldset disabled={saving} className="space-y-4">
          <div className="grid gap-3 sm:grid-cols-2"><label>{t.number} *<input required maxLength={64} className={control} value={number} onChange={e => setNumber(e.target.value)} {...errorProps} /></label>{form === 'receipts' && <label>{t.order} *<select required className={control} value={orderId} onChange={e => { setOrderId(e.target.value); setLines([makeLine()]); }} {...errorProps}><option value="">{t.choose}</option>{catalog.purchase_orders.map(po => <option key={po.id} value={po.id}>{po.po_no} · {po.currency}</option>)}</select></label>}</div>
          {form === 'receipts' && <label className="block">{t.comment}<textarea maxLength={4000} className={control} value={comment} onChange={e => setComment(e.target.value)} /></label>}
          {((form === 'receipts' && !catalog.purchase_orders.length) || (form === 'counts' && !catalog.skus.length)) && <p>{t.noOptions}</p>}
          {lines.map((line, index) => {
            const poItem = order?.items.find(x => x.id === Number(line.itemId));
            return <fieldset key={line.key} className="min-w-0 space-y-3 rounded-lg border border-slate-300 p-3 dark:border-slate-600"><legend className="px-1 font-medium">{t.line} {index + 1}</legend>
              <div className="grid gap-3 sm:grid-cols-2"><label>{t.sku} *<select required className={control} value={line.itemId} onChange={e => updateLine(line.key, 'itemId', e.target.value)} {...errorProps}><option value="">{t.choose}</option>{form === 'receipts' ? order?.items.filter(item => item.ordered_qty > item.received_qty).map(item => <option key={item.id} value={item.id}>{item.sku_code} · {name(item)}</option>) : catalog.skus.map(item => <option key={item.id} value={item.id}>{item.sku_code} · {name(item)}</option>)}</select></label><label>{form === 'receipts' ? t.qty : t.actual} *<input required type="number" min={form === 'receipts' ? '1' : '0'} max="99999999999" step={form === 'receipts' ? '1' : '0.001'} className={control} value={line.qty} onChange={e => updateLine(line.key, 'qty', e.target.value)} {...errorProps} /></label>
                {form === 'receipts' && <><label>{t.location}<select className={control} value={line.locationId} onChange={e => updateLine(line.key, 'locationId', e.target.value)}><option value="">{t.unlocated}</option>{warehouse?.locations.map(location => <option key={location.id} value={location.id}>{location.code}</option>)}</select></label><label>{t.batch}<input maxLength={128} className={control} value={line.batch} onChange={e => updateLine(line.key, 'batch', e.target.value)} {...errorProps} /></label><label>{t.expiryDate}<input type="date" className={control} value={line.expiry} onChange={e => updateLine(line.key, 'expiry', e.target.value)} {...errorProps} /></label></>}
              </div>
              {poItem && <dl className="flex flex-wrap gap-4 text-sm">{[[t.ordered,poItem.ordered_qty],[t.received,poItem.received_qty],[t.remaining,poItem.ordered_qty - poItem.received_qty]].map(([label,value]) => <div key={label}><dt className="text-slate-600 dark:text-slate-300">{label}</dt><dd>{formatNumber(value)}</dd></div>)}</dl>}
              <label className="block">{t.reason}<textarea className={control} maxLength={4000} value={line.reason} onChange={e => updateLine(line.key, 'reason', e.target.value)} {...errorProps} /></label><button type="button" className={button} aria-label={`${t.remove} ${index + 1}`} disabled={lines.length === 1} onClick={() => setLines(lines.filter(x => x.key !== line.key))}>{t.remove}</button>
            </fieldset>;
          })}
          <div className="flex flex-wrap gap-2"><button type="button" className={button} disabled={lines.length >= 100} onClick={() => setLines([...lines, makeLine()])}>{t.add}</button><button className={primary} disabled={(form === 'receipts' && !catalog.purchase_orders.length) || (form === 'counts' && !catalog.skus.length)}>{saving ? t.saving : t.save}</button><button type="button" className={button} onClick={() => setForm(null)}>{t.cancel}</button></div>
        </fieldset>
      </form>}
      {view === 'counts' && <p className="text-sm text-amber-900 dark:text-amber-200">{t.countHelp}</p>}
      {view === 'expiry' && <label className="block max-w-xs text-sm">{t.days}<select value={days} disabled={saving} className={control} onChange={e => setDays(e.target.value)}>{[7,14,30,60,90,180,365].map(value => <option key={value} value={value}>{value}</option>)}</select></label>}
      <div aria-busy={loading} className="min-w-0">{loading ? <p role="status">{t.loading}</p> : view !== 'expiry' && rowCount === 0 ? <p>{t.empty}</p> : <>
        {view === 'inventory' && <DataTable caption={t.inventory} headers={[t.sku,t.location,t.qty,t.batches,...(inventoryCost ? [t.cost] : [])]} rows={inventory.map(item => ({key:item.id,cells:[<span key="name">{item.sku_code}<span className="block">{name(item)}</span></span>,item.location_code || t.unlocated,formatNumber(item.qty),item.batches.length ? <ul key="batches" className="space-y-2">{item.batches.map(batch => <li key={batch.batch_no}>{batch.batch_no} · {formatNumber(batch.qty)} · {formatDate(batch.expiry_date)}</li>)}</ul> : '—',...(inventoryCost ? [item.avg_cost === undefined ? '—' : formatNumber(item.avg_cost)] : [])]}))} />}
        {view === 'movements' && <DataTable caption={t.movements} headers={[t.date,t.sku,t.location,t.type,t.delta,t.reason,t.source,...(movementCost ? [t.cost] : [])]} rows={movements.map(item => ({key:item.id,cells:[formatDate(item.posted_at),`${item.sku_code} · ${name(item)}`,item.location_code || t.unlocated,kindLabel(item.movement_type),`${Number(item.qty_delta) > 0 ? '+' : ''}${formatNumber(item.qty_delta)}`,item.reason || '—',<div key="source"><p>{sourceLabel(item.source_type)} · {item.source_no || `#${item.source_id}`}</p>{((item.source_type === 'purchase_receipt' && canView('receipts')) || (item.source_type === 'stock_count' && canView('counts')) || (item.source_type === 'stock_transfer' && canView('transfers')) || (item.source_type === 'stock_writeoff' && canView('writeoffs'))) && <button className={`${button} mt-2`} disabled={saving} onClick={e => void sourceOpen(item,e.currentTarget)}>{t.open}</button>}</div>,...(movementCost ? [item.unit_cost === undefined ? '—' : formatNumber(item.unit_cost)] : [])]}))} />}
        {view === 'receipts' && <DataTable caption={t.receipts} headers={[t.number,t.order,t.status,t.date,t.action]} rows={receipts.map(item => ({key:item.id,cells:[item.receipt_no,item.po_no,status(item.status),formatDate(item.received_at),<button key="open" className={button} disabled={saving} onClick={e => showDocument('receipts',item,e.currentTarget)}>{t.open}</button>]}))} />}
        {view === 'counts' && <DataTable caption={t.counts} headers={[t.number,t.status,t.date,t.action]} rows={counts.map(item => ({key:item.id,cells:[item.count_no,status(item.status),formatDate(item.created_at),<button key="open" className={button} disabled={saving} onClick={e => showDocument('counts',item,e.currentTarget)}>{t.open}</button>]}))} />}
        {view === 'expiry' && expiry && <div className="space-y-5">{expiry.truncated && <p role="status" className="text-amber-900 dark:text-amber-200">{t.truncated}</p>}<h2 className="text-lg font-semibold">{t.batches}</h2>{!expiry.batches.length ? <p>{t.empty}</p> : <DataTable caption={t.batches} headers={[t.sku,t.location,t.batch,t.qty,t.expiryDate,t.status]} rows={expiry.batches.map(item => ({key:item.id,cells:[`${item.sku_code} · ${name(item)}`,item.location_code || t.unlocated,item.batch_no,formatNumber(item.qty),formatDate(item.expiry_date),item.expired ? t.expired : t.soon]}))} />}<h2 className="text-lg font-semibold">{t.certificates}</h2>{!expiry.certificates.length ? <p>{t.empty}</p> : <DataTable caption={t.certificates} headers={[t.sku,t.number,t.expiryDate,t.status]} rows={expiry.certificates.map(item => ({key:item.id,cells:[item.sku_code,item.number,formatDate(item.expires_at),item.expired ? t.expired : t.soon]}))} />}</div>}
      </>}</div>
      {view !== 'expiry' && total > 0 && <div className="flex flex-wrap items-center gap-3"><button className={button} disabled={saving || loading || offset === 0} onClick={() => { setOffset(Math.max(0,offset - 20)); setDocument(null); }}>{t.previous}</button><span className="text-sm">{offset + 1}–{offset + rowCount} {t.of} {total}</span><button className={button} disabled={saving || loading || offset + rowCount >= total} onClick={() => { setOffset(offset + 20); setDocument(null); }}>{t.next}</button></div>}
      {document && <section aria-labelledby="warehouse-details" className={panel}><div className="flex flex-wrap items-start justify-between gap-3"><h2 id="warehouse-details" tabIndex={-1} ref={detailsHeading} className="min-w-0 break-words text-lg font-semibold focus-visible:outline-2 focus-visible:outline-blue-600">{t.details}: {document.kind === 'receipts' ? document.item.receipt_no : document.item.count_no}</h2><button className={button} disabled={saving} onClick={() => { setDocument(null); if (trigger.current?.isConnected) trigger.current.focus(); else heading.current?.focus(); }}>{t.close}</button></div><p>{status(document.item.status)}</p>
        {document.kind === 'receipts' ? <><p className="break-words">{t.order}: {document.item.po_no}</p><p className="break-words whitespace-pre-wrap">{document.item.comment}</p><DataTable caption={t.receipts} headers={[t.sku,t.qty,t.location,t.batch,t.expiryDate,t.reason,...(document.item.items.some(x => x.unit_cost !== undefined) ? [t.cost] : [])]} rows={document.item.items.map(item => ({key:item.id,cells:[`${item.sku_code} · ${name(item)}`,formatNumber(item.qty),item.location_code || t.unlocated,item.batch_no || '—',item.expiry_date ? formatDate(item.expiry_date) : '—',item.discrepancy_reason || '—',...(document.item.items.some(x => x.unit_cost !== undefined) ? [item.unit_cost === undefined ? '—' : formatNumber(item.unit_cost)] : [])]}))} /><p className="text-sm text-slate-600 dark:text-slate-300">{t.postHelp}</p>{document.item.allowed_actions.includes('post') && <button className={primary} disabled={saving} onClick={() => void run(() => api.postWarehouseReceipt(document.item.id))}>{saving ? t.saving : t.post}</button>}</> : <><p className="text-sm text-amber-900 dark:text-amber-200">{t.countHelp}</p><DataTable caption={t.counts} headers={[t.sku,t.system,t.actual,t.difference,t.reason]} rows={document.item.items.map(item => ({key:item.sku_id,cells:[`${item.sku_code} · ${name(item)}`,formatNumber(item.system_qty),formatNumber(item.actual_qty),formatNumber(Number(item.actual_qty) - Number(item.system_qty)),item.reason || '—']}))} />{document.item.allowed_actions.includes('approve') && <button className={primary} disabled={saving} onClick={() => void run(() => api.approveWarehouseCount(document.item.id))}>{saving ? t.saving : t.approve}</button>}</>}
      </section>}
      </>}
    </>}
  </section>;
}
