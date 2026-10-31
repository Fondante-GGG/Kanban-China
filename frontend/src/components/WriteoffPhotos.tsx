'use client';

import Image from 'next/image';
import { useEffect, useRef, useState } from 'react';
import { api } from '@/lib/api';
import { writeoffTranslations } from '@/lib/writeoff-i18n';
import type { LanguageCode, WriteoffPhoto } from '@/types';

const button = 'min-h-11 rounded-lg border border-slate-300 px-4 py-2 text-sm font-semibold hover:bg-slate-100 dark:border-slate-600 dark:hover:bg-slate-800 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600 disabled:opacity-50';
const primary = 'min-h-11 rounded-lg bg-blue-700 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-800 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600 disabled:opacity-50';
const localeFor = (lang: LanguageCode) => ({ ru:'ru-RU', ky:'ky-KG', 'zh-Hans':'zh-CN', 'zh-Hant':'zh-TW' })[lang];

function PrivatePhoto({ id, photo, index, lang, busy, canRemove, onRemove, onDenied, errorText }: { id:number; photo:WriteoffPhoto; index:number; lang:LanguageCode; busy:boolean; canRemove:boolean; onRemove:(photo:WriteoffPhoto)=>void; onDenied:()=>void; errorText:(cause:unknown)=>string }) {
  const t = writeoffTranslations[lang];
  const [url, setUrl] = useState(''), [loading, setLoading] = useState(false), [error, setError] = useState('');
  const request = useRef<AbortController | null>(null), objectUrl = useRef('');
  const mounted = useRef(true);
  const clear = () => { request.current?.abort(); if(objectUrl.current) URL.revokeObjectURL(objectUrl.current); objectUrl.current='';setUrl(''); };
  useEffect(() => { mounted.current=true; return () => { mounted.current=false; request.current?.abort();if(objectUrl.current) URL.revokeObjectURL(objectUrl.current); }; }, []);
  const preview = async () => {
    if(url){clear();return;}
    request.current?.abort(); const controller=new AbortController();request.current=controller;setLoading(true);setError('');
    try {
      const blob=await api.getWriteoffPhoto(id,photo.id,controller.signal);
      if(!mounted.current || controller.signal.aborted)return;
      const next=URL.createObjectURL(blob);if(objectUrl.current)URL.revokeObjectURL(objectUrl.current);objectUrl.current=next;setUrl(next);
    } catch(cause) {
      if(!mounted.current || controller.signal.aborted)return;
      if([401,403].includes((cause as {status?:number}).status || 0))onDenied();
      else setError(errorText(cause));
    } finally { if(mounted.current && !controller.signal.aborted)setLoading(false); }
  };
  return <figure className="min-w-0 space-y-3 rounded-lg border border-slate-300 p-3 dark:border-slate-600">
    <figcaption className="break-words text-sm"><span className="font-semibold">{t.photo} {index+1}</span><span className="mt-1 block">{photo.file_name}</span><span>{new Intl.NumberFormat(localeFor(lang),{style:'unit',unit:'megabyte',maximumFractionDigits:2}).format(photo.size/1000/1000)}</span></figcaption>
    <div className="flex flex-wrap gap-2"><button type="button" className={button} disabled={busy || loading} onClick={()=>void preview()} aria-label={`${url?t.hidePhoto:t.showPhoto} ${index+1}`}>{loading?t.loading:url?t.hidePhoto:t.showPhoto}</button>{canRemove&&<button type="button" className={button} disabled={busy || loading} onClick={()=>onRemove(photo)} aria-label={`${t.removePhoto} ${index+1}`}>{t.removePhoto}</button>}</div>
    {error&&<p role="alert" className="text-sm text-rose-800 dark:text-rose-200">{error}</p>}
    {url&&<><div className="relative aspect-[4/3] w-full"><Image src={url} fill unoptimized sizes="(max-width: 640px) 100vw, 400px" className="object-contain" alt={`${t.photo} ${index+1}`} /></div><a href={url} download={photo.file_name} className={`${button} inline-flex items-center`}>{t.download}</a></>}
  </figure>;
}

export function WriteoffPhotos({ id, photos, lang, busy, canUpload, canRemove, onUpload, onRemove, onDenied, errorText }: { id:number; photos:WriteoffPhoto[]; lang:LanguageCode; busy:boolean; canUpload:boolean; canRemove:boolean; onUpload:(file:File)=>Promise<boolean>; onRemove:(photo:WriteoffPhoto)=>void; onDenied:()=>void; errorText:(cause:unknown)=>string }) {
  const t=writeoffTranslations[lang];
  const [file,setFile]=useState<File|null>(null),[fileUrl,setFileUrl]=useState(''),[error,setError]=useState('');
  const input=useRef<HTMLInputElement>(null);
  useEffect(()=>{if(!file){setFileUrl('');return;}const url=URL.createObjectURL(file);setFileUrl(url);return()=>URL.revokeObjectURL(url);},[file]);
  const choose=(next:File|null)=>{setError('');if(next&&(next.size<=0 || next.size>10*1024*1024 || !['image/jpeg','image/png','image/webp'].includes(next.type))){setError(t.invalidPhoto);setFile(null);return;}setFile(next);};
  const upload=async()=>{if(!file)return;if(await onUpload(file)){setFile(null);if(input.current)input.current.value='';input.current?.focus();}};
  return <section aria-labelledby="writeoff-photos" className="space-y-4 border-t border-slate-300 pt-4 dark:border-slate-600">
    <h4 id="writeoff-photos" tabIndex={-1} className="text-lg font-semibold">{t.photos}</h4><p className="text-sm">{t.photoCount}: {photos.length}</p>{!photos.length&&<p className="text-sm text-amber-900 dark:text-amber-200">{t.photoRequired}</p>}
    {canUpload&&<div className="space-y-3"><label className="block text-sm font-medium">{t.addPhoto}<input ref={input} type="file" accept="image/jpeg,image/png,image/webp" disabled={busy || photos.length>=5} aria-invalid={!!error} aria-describedby={error?'writeoff-photo-error':'writeoff-photo-help'} className="mt-1 block min-h-11 w-full min-w-0 rounded-lg border border-slate-300 p-2 text-sm dark:border-slate-600 focus-visible:outline-2 focus-visible:outline-blue-600" onChange={e=>choose(e.target.files?.[0]||null)}/></label><p id="writeoff-photo-help" className="text-sm text-slate-600 dark:text-slate-300">{t.photoHelp}</p>{error&&<p id="writeoff-photo-error" role="alert" className="text-sm text-rose-800 dark:text-rose-200">{error}</p>}
      {file&&<div className="space-y-3"><p className="break-words text-sm">{file.name} · {new Intl.NumberFormat(localeFor(lang),{style:'unit',unit:'megabyte',maximumFractionDigits:2}).format(file.size/1000/1000)} — {t.selectedFile}</p>{fileUrl&&<div className="relative aspect-[4/3] w-full max-w-sm"><Image src={fileUrl} fill unoptimized sizes="400px" className="object-contain" alt={t.notUploaded}/></div>}<button type="button" className={primary} disabled={busy || photos.length>=5} onClick={()=>void upload()}>{busy?t.uploading:t.upload}</button></div>}
    </div>}
    <div className="grid min-w-0 gap-4 sm:grid-cols-2 lg:grid-cols-3">{photos.map((photo,index)=><PrivatePhoto key={`${id}:${photo.id}`} id={id} photo={photo} index={index} lang={lang} busy={busy} canRemove={canRemove} onRemove={onRemove} onDenied={onDenied} errorText={errorText}/>)}</div>
  </section>;
}
