'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { ReturnPhotos } from './ReturnPhotos';
import { SupplierReturnCorrections, clearCorrectionSession } from './SupplierReturnCorrections';
import { supplierReturnCorrectionTranslations } from '@/lib/supplier-return-corrections-i18n';
import { api } from '@/lib/api';
import { supplierReturnTranslations } from '@/lib/supplier-returns-i18n';
import type { LanguageCode, SupplierReturnFinance } from '@/types';

const button='min-h-11 rounded-lg border border-slate-300 px-4 py-2 text-sm font-semibold hover:bg-slate-100 dark:border-slate-600 dark:hover:bg-slate-800 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600 disabled:opacity-50';
export function SupplierReturnFinanceQueue({lang,initialReturnId,userId}:{lang:LanguageCode;initialReturnId?:number;userId:number}) {
  const t=supplierReturnTranslations[lang];
  const ct=supplierReturnCorrectionTranslations[lang];
  const [expanded,setExpanded]=useState<number|null>(null);
  const [items,setItems]=useState<SupplierReturnFinance[]>([]),[count,setCount]=useState(0),[offset,setOffset]=useState(0),[loading,setLoading]=useState(true),[error,setError]=useState('');
  const [lookup,setLookup]=useState<number|undefined>(initialReturnId);
  const title=useRef<HTMLHeadingElement>(null);
  const generation=useRef(0),mounted=useRef(true);
  const load=useCallback(async()=>{const request=++generation.current;setLoading(true);setError('');try{const result=await api.getSupplierReturnFinance({limit:20,offset,return_id:lookup});if(mounted.current&&request===generation.current){setItems(result.items);setCount(result.count);if(lookup)requestAnimationFrame(()=>title.current?.focus());}}catch(cause){if(!mounted.current||request!==generation.current)return;setItems([]);setCount(0);setError([401,403].includes((cause as {status?:number}).status||0)?t.forbidden:t.failed);}finally{if(mounted.current&&request===generation.current)setLoading(false);}},[offset,t,lookup]);
  const invalidate=useCallback(()=>{generation.current++;},[]);
  useEffect(()=>{mounted.current=true;return()=>{mounted.current=false;invalidate();};},[invalidate]);
  useEffect(()=>{void load();},[load]);
  const denied=useCallback(()=>{generation.current++;setExpanded(null);setItems([]);setCount(0);setLoading(false);setError(t.forbidden);},[t.forbidden]);
  useEffect(()=>{clearCorrectionSession(userId);const changed=()=>{clearCorrectionSession(userId);denied();};window.addEventListener('kanban-auth-change',changed);return()=>window.removeEventListener('kanban-auth-change',changed);},[userId,denied]);
  const locale={ru:'ru-RU',ky:'ky-KG','zh-Hans':'zh-CN','zh-Hant':'zh-TW'}[lang];
  const date=(value:string)=>new Intl.DateTimeFormat(locale,{dateStyle:'medium',timeStyle:'short'}).format(new Date(value));
  const number=(value:string)=>new Intl.NumberFormat(locale,{maximumFractionDigits:6}).format(Number(value));
  return <section className="min-w-0 space-y-4 rounded-xl border border-slate-300 bg-white p-4 text-slate-950 dark:border-slate-600 dark:bg-slate-900 dark:text-slate-100" aria-labelledby="supplier-return-finance-heading" aria-busy={loading}>
    <div className="flex flex-wrap items-start justify-between gap-3"><h2 id="supplier-return-finance-heading" ref={title} tabIndex={-1} className="min-w-0 break-words text-xl font-bold focus-visible:outline-2 focus-visible:outline-blue-600">{t.financeTitle}</h2><button type="button" className={button} disabled={loading} onClick={()=>void load()}>{t.refresh}</button></div>
    <p className="text-sm text-slate-600 dark:text-slate-300">{t.financeHelp}</p>{lookup&&<button type="button" className={button} disabled={loading} onClick={()=>{setLookup(undefined);setOffset(0);}}>{t.financeAll}</button>}
    {error&&<div><p role="alert" className="text-rose-800 dark:text-rose-200">{error}</p><button className={`${button} mt-2`} disabled={loading} onClick={()=>void load()}>{t.retry}</button></div>}
    {loading?<p role="status">{t.loading}</p>:!error&&!items.length?<p>{lookup?t.financeMissing:t.financeEmpty}</p>:<div className="grid min-w-0 gap-4 lg:grid-cols-2">{items.map(item=><article key={item.id} className="min-w-0 space-y-3 rounded-lg border border-slate-300 p-4 dark:border-slate-600"><h3 className="break-words font-semibold">{t.details}: {item.return_no}</h3><p className="text-amber-900 dark:text-amber-200">{t.financePending}</p><dl className="grid min-w-0 gap-3 text-sm sm:grid-cols-2">{[[t.receipt,item.receipt_no],[t.supplier,item.supplier_name],[t.date,date(item.posted_at)],[t.valuation,number(item.stock_valuation)],[t.sourceCurrency,item.source_currency]].map(([label,value])=><div key={label} className="min-w-0"><dt className="text-slate-600 dark:text-slate-300">{label}</dt><dd className="break-words">{value}</dd></div>)}</dl><p className="text-sm text-amber-900 dark:text-amber-200">{t.currencyUnresolved}</p><ul className="space-y-2 text-sm">{item.items.map((row,index)=><li key={`${row.receipt_item_id}:${index}`} className="break-words">{row.sku_code} · {(lang==='ky'?row.name_ky:lang.startsWith('zh')?row.name_zh:row.name_ru)||row.name_ru} · {t.qty}: {number(row.qty)}</li>)}</ul><ReturnPhotos key={item.id} id={item.id} photos={item.photos} required={false} lang={lang} busy={loading} canUpload={false} canRemove={false} onUpload={async()=>false} onRemove={()=>{}} onDenied={denied} errorText={()=>t.failed} loadPhoto={(id,photoId,signal)=>api.getSupplierReturnFinancePhoto(id,photoId,signal)} idPrefix={`finance-return-${item.id}`}/><button type="button" className={button} aria-expanded={expanded===item.id} aria-controls={`return-corrections-${userId}-${item.id}`} onClick={()=>setExpanded(expanded===item.id?null:item.id)}>{expanded===item.id?ct.hide:ct.title}</button><div id={`return-corrections-${userId}-${item.id}`}>{expanded===item.id&&<SupplierReturnCorrections key={`${userId}:${item.id}`} item={item} userId={userId} lang={lang} onDenied={denied}/>}</div></article>)}</div>}
    {count>0&&<div className="flex flex-wrap items-center gap-3"><button className={button} disabled={loading||offset===0} onClick={()=>setOffset(Math.max(0,offset-20))}>{t.previous}</button><span>{offset+1}–{offset+items.length} {t.of} {count}</span><button className={button} disabled={loading||offset+items.length>=count} onClick={()=>setOffset(offset+20)}>{t.next}</button></div>}
  </section>;
}
