'use client';
import { ReactNode, useEffect, useRef } from 'react';
import { LanguageCode } from '@/types';
import { hrTranslations } from '@/lib/i18n';

export function AccessibleDialog({ lang, title, children, onClose }: { lang: LanguageCode; title: string; children: ReactNode; onClose: () => void }) {
  const dialog = useRef<HTMLDivElement>(null);
  const previousFocus = useRef<HTMLElement | null>(null);
  useEffect(() => {
    previousFocus.current = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    dialog.current?.focus();
    const key = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
      if (e.key !== 'Tab' || !dialog.current) return;
      const nodes = [...dialog.current.querySelectorAll<HTMLElement>('button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])')];
      if (!nodes.length) return;
      const first = nodes[0], last = nodes[nodes.length - 1];
      if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
      else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
    };
    document.addEventListener('keydown', key);
    return () => { document.removeEventListener('keydown', key); previousFocus.current?.focus(); };
  }, [onClose]);
  return <div className="fixed inset-0 z-50 grid place-items-center bg-slate-950/50 p-4" onMouseDown={e => { if (e.target === e.currentTarget) onClose(); }}><div ref={dialog} role="dialog" aria-modal="true" aria-labelledby="dialog-title" tabIndex={-1} className="w-full max-w-lg rounded-xl bg-white p-5 text-slate-950 shadow-2xl dark:bg-slate-900 dark:text-white"><div className="mb-4 flex items-center justify-between gap-4"><h2 id="dialog-title" className="text-lg font-bold">{title}</h2><button type="button" onClick={onClose} aria-label={hrTranslations[lang].close} className="rounded p-1 text-slate-600 hover:bg-slate-100 dark:text-slate-200 dark:hover:bg-slate-800">×</button></div>{children}</div></div>;
}
