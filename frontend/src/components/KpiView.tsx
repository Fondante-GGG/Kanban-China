'use client';

import { FormEvent, useCallback, useEffect, useRef, useState } from 'react';
import { api } from '@/lib/api';
import { kpiTranslations } from '@/lib/kpi-i18n';
import type { KpiAssignee, KpiComments, KpiCycle, KpiStatus, KpiTask, KpiTemplate, KpiTemplateItem, LanguageCode, User } from '@/types';

const control = 'mt-1 min-h-11 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-slate-950 dark:border-slate-600 dark:bg-slate-950 dark:text-slate-100 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600';
const button = 'min-h-11 rounded-lg border border-slate-300 px-4 py-2 text-sm font-semibold dark:border-slate-600 hover:bg-slate-100 dark:hover:bg-slate-800 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600 disabled:opacity-50';
const primary = `${button.replace('hover:bg-slate-100 dark:hover:bg-slate-800', '')} border-blue-700 bg-blue-700 text-white hover:bg-blue-800 dark:border-blue-600 dark:hover:bg-blue-800`;
const blankComments = (): KpiComments => ({ ru: '', zh: '', ky: '' });
const blankItem = (): KpiTemplateItem => ({ name_ru: '', name_zh: '', name_ky: '', weight: '100', formula: 'manual' });
const localeFor = (lang: LanguageCode) => ({ ru: 'ru-RU', ky: 'ky-KG', 'zh-Hans': 'zh-CN', 'zh-Hant': 'zh-TW' })[lang];

export function KpiView({ lang, currentUser }: { lang: LanguageCode; currentUser: User }) {
  const t = kpiTranslations[lang];
  const permissions = currentUser.system_permissions || [];
  const manage = currentUser.role === 'general_director' || permissions.includes('kpi.manage');
  const allowed = manage || permissions.includes('kpi.read');
  const [view, setView] = useState<'evaluations' | 'archive' | 'templates'>('evaluations');
  const [tasks, setTasks] = useState<KpiTask[]>([]);
  const [templates, setTemplates] = useState<KpiTemplate[]>([]);
  const [assignees, setAssignees] = useState<KpiAssignee[]>([]);
  const [loading, setLoading] = useState(true), [saving, setSaving] = useState(false);
  const [error, setError] = useState(''), [notice, setNotice] = useState('');
  const [invalid, setInvalid] = useState<'score' | 'comments' | 'template' | 'assign' | null>(null);
  const [year, setYear] = useState(''), [status, setStatus] = useState(''), [offset, setOffset] = useState(0), [count, setCount] = useState(0);
  const [selected, setSelected] = useState<KpiTask | null>(null);
  const [score, setScore] = useState(''), [comments, setComments] = useState<KpiComments>(blankComments);
  const [form, setForm] = useState<'template' | 'assign' | null>(null);
  const [templateName, setTemplateName] = useState(''), [position, setPosition] = useState(''), [cycle, setCycle] = useState<KpiCycle>('month');
  const [items, setItems] = useState<KpiTemplateItem[]>([blankItem()]);
  const [employeeId, setEmployeeId] = useState(''), [templateId, setTemplateId] = useState('');
  const [assignYear, setAssignYear] = useState(String(new Date().getFullYear())), [period, setPeriod] = useState('01');
  const detailsHeading = useRef<HTMLHeadingElement>(null);
  const openTrigger = useRef<HTMLButtonElement | null>(null);
  const requestId = useRef(0);
  const chosenTemplate = templates.find(x => x.id === Number(templateId));
  const statuses: KpiStatus[] = ['self_review', 'manager_review', 'senior_review', 'confirmed'];
  const statusLabel = (value: KpiStatus) => ({ self_review: t.self, manager_review: t.manager, senior_review: t.senior, confirmed: t.confirmed })[value];
  const cycleLabel = (value: KpiCycle) => ({ month: t.month, quarter: t.quarter, year: t.annual })[value];
  const displayName = (ru: string, ky: string, zh: string) => (lang === 'ky' ? ky : lang.startsWith('zh') ? zh : ru) || ru || ky || zh || t.unknown;
  const formatDate = (value: string) => new Intl.DateTimeFormat(localeFor(lang), { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value));
  const formatScore = (value: string | null) => value === null ? '—' : new Intl.NumberFormat(localeFor(lang), { maximumFractionDigits: 2 }).format(Number(value));
  const errorText = useCallback((cause: unknown) => {
    const e = cause as { code?: string; status?: number };
    if (e?.code === 'validation_error') return t.validation;
    if (e?.code === 'duplicate_task') return t.duplicate;
    if (e?.code === 'invalid_transition' || e?.status === 409) return t.conflict;
    if (e?.status === 401 || e?.status === 403 || e?.code === 'permission_denied') return t.forbidden;
    return t.failed;
  }, [t]);
  const load = useCallback(async () => {
    if (!allowed) { setLoading(false); return; }
    const id = ++requestId.current;
    setLoading(true); setError('');
    try {
      const response = await api.getKpiTasks({ archived: view === 'archive', year: year ? Number(year) : undefined, status, offset, limit: 20 });
      if (id !== requestId.current) return;
      setTasks(response.items); setCount(response.count);
      setSelected(old => old ? response.items.find(x => x.id === old.id) || null : null);
    } catch (cause) { if (id === requestId.current) { setError(errorText(cause)); setTasks([]); setSelected(null); setCount(0); if ((cause as { status?: number }).status === 403) { setForm(null); setTemplates([]); setAssignees([]); } } }
    finally { if (id === requestId.current) setLoading(false); }
  }, [allowed, view, year, status, offset, errorText]);
  const loadOptions = useCallback(async () => {
    if (!allowed) return;
    try {
      const response = await api.getKpiTemplates(); setTemplates(response.items);
      if (manage) setAssignees((await api.getKpiAssignees()).items);
    } catch (cause) { setError(errorText(cause)); }
  }, [allowed, manage, errorText]);
  useEffect(() => { void load(); }, [load]);
  useEffect(() => { void loadOptions(); }, [loadOptions]);
  const selectedId = selected?.id;
  useEffect(() => { if (selectedId) detailsHeading.current?.focus(); }, [selectedId]);
  const run = async (action: () => Promise<unknown>, close = false) => {
    setSaving(true); setError(''); setNotice(''); setInvalid(null);
    try { await action(); setNotice(t.success); if (close) setForm(null); await load(); await loadOptions(); }
    catch (cause) { const code = (cause as { code?: string; status?: number }); if (code.code === 'invalid_transition' || code.status === 403 || code.status === 409) await load(); setError(errorText(cause)); }
    finally { setSaving(false); }
  };
  const createTemplate = (event: FormEvent) => {
    event.preventDefault();
    const weights = items.map(x => Number(x.weight));
    if (!templateName.trim() || !position.trim() || items.some(x => !x.name_ru.trim()) || weights.some(x => !Number.isFinite(x) || x <= 0) || Math.abs(weights.reduce((a, b) => a + b, 0) - 100) > 0.001) { setInvalid('template'); setError(t.namesRequired); return; }
    void run(() => api.createKpiTemplate({ name: templateName, position_code: position, cycle, items }), true);
  };
  const assign = (event: FormEvent) => {
    event.preventDefault(); if (!employeeId || !chosenTemplate) { setInvalid('assign'); setError(t.employeeRequired); return; }
    void run(() => api.createKpiTask({ employee_id: Number(employeeId), template_id: Number(templateId), year: Number(assignYear), period: chosenTemplate.cycle === 'year' ? 'year' : period }), true);
  };
  const scoreTask = (event: FormEvent) => {
    event.preventDefault(); if (!selected) return;
    if (!/^\d+(\.\d{1,2})?$/.test(score) || Number(score) > 100) { setInvalid('score'); setError(t.numberRequired); return; }
    const stage = selected.allowed_actions.includes('self_score') ? 'self' : 'manager';
    void run(() => api.scoreKpiTask(selected.id, { stage, score, comment_ru: comments.ru, comment_zh: comments.zh, comment_ky: comments.ky }));
  };
  const review = (decision: 'approve' | 'return') => {
    if (!selected) return;
    if (decision === 'return' && !Object.values(comments).some(x => x.trim())) { setInvalid('comments'); setError(t.returnRequired); return; }
    void run(() => api.reviewKpiTask(selected.id, decision, comments));
  };
  const commentFields = <div className="grid gap-3 sm:grid-cols-3">{(['ru', 'ky', 'zh'] as const).map(code => <label key={code} className="text-sm">{code === 'ru' ? t.commentRu : code === 'ky' ? t.commentKy : t.commentZh}<textarea disabled={saving} aria-invalid={invalid === 'comments'} aria-describedby={invalid === 'comments' ? 'kpi-error' : undefined} className={control} value={comments[code]} onChange={e => setComments({ ...comments, [code]: e.target.value })} maxLength={4000} /></label>)}</div>;
  if (!allowed) return <p role="alert" className="p-6">{t.forbidden}</p>;
  return <section className="mx-auto max-w-7xl space-y-5 p-4 pb-24 text-slate-950 dark:text-slate-100 sm:p-6 sm:pb-24">
    <header className="flex flex-wrap items-start justify-between gap-4"><div><h1 className="text-2xl font-bold">{t.title}</h1><p className="mt-1 text-sm text-slate-600 dark:text-slate-300">{t.subtitle}</p></div><div className="flex flex-wrap gap-2"><button className={button} disabled={loading || saving} onClick={() => { void load(); void loadOptions(); }}>{t.refresh}</button>{manage && <><button className={button} onClick={() => { setForm('assign'); setSelected(null); }}>{t.assign}</button><button className={primary} onClick={() => { setForm('template'); setSelected(null); }}>{t.createTemplate}</button></>}</div></header>
    <div className="flex flex-wrap gap-2">{(['evaluations', 'archive', ...(manage ? ['templates'] : [])] as Array<typeof view>).map(value => <button key={value} aria-pressed={view === value} disabled={saving} className={view === value ? primary : button} onClick={() => { setView(value); setOffset(0); setSelected(null); }}>{t[value]}</button>)}</div>
    {error && <p id="kpi-error" role="alert" className="rounded-lg border border-rose-300 bg-rose-50 p-3 text-rose-800 dark:border-rose-700 dark:bg-rose-950 dark:text-rose-200">{error}</p>}
    <p role="status" className="text-sm text-emerald-800 dark:text-emerald-200">{notice}</p>
    {form === 'template' && <form onSubmit={createTemplate} className="space-y-4 rounded-xl border border-slate-300 bg-white p-4 dark:border-slate-600 dark:bg-slate-900"><h2 className="text-lg font-semibold">{t.createTemplate}</h2><p className="text-sm text-slate-600 dark:text-slate-300">{t.manualHelp}</p><div className="grid gap-3 sm:grid-cols-3"><label>{t.name}<input required disabled={saving} aria-invalid={invalid === 'template'} aria-describedby={invalid === 'template' ? 'kpi-error' : undefined} className={control} value={templateName} onChange={e => setTemplateName(e.target.value)} maxLength={255} /></label><label>{t.position}<input required disabled={saving} aria-invalid={invalid === 'template'} aria-describedby={invalid === 'template' ? 'kpi-error' : undefined} className={control} value={position} onChange={e => setPosition(e.target.value)} maxLength={128} /></label><label>{t.cycle}<select className={control} value={cycle} onChange={e => setCycle(e.target.value as KpiCycle)}>{(['month', 'quarter', 'year'] as const).map(c => <option key={c} value={c}>{cycleLabel(c)}</option>)}</select></label></div>{items.map((item, index) => <fieldset key={index} className="rounded-lg border border-slate-300 p-3 dark:border-slate-600"><legend className="px-1 font-medium">{t.indicator} {index + 1}</legend><div className="grid gap-3 sm:grid-cols-2">{(['name_ru', 'name_ky', 'name_zh', 'weight'] as const).map(key => <label key={key} className="text-sm">{({name_ru:t.nameRu,name_ky:t.nameKy,name_zh:t.nameZh,weight:t.weight})[key]}<input disabled={saving} aria-invalid={invalid === 'template'} aria-describedby={invalid === 'template' ? 'kpi-error' : undefined} required={key === 'name_ru' || key === 'weight'} type={key === 'weight' ? 'number' : 'text'} min={key === 'weight' ? '0.01' : undefined} max={key === 'weight' ? '100' : undefined} step={key === 'weight' ? '0.01' : undefined} className={control} value={item[key]} onChange={e => setItems(items.map((x, n) => n === index ? { ...x, [key]: e.target.value } : x))} /></label>)}</div><p className="my-2 text-sm">{t.manual}</p><button type="button" className={button} disabled={items.length === 1 || saving} aria-label={`${t.remove} ${index + 1}`} onClick={() => setItems(items.filter((_, n) => n !== index))}>{t.remove}</button></fieldset>)}<p>{t.total}: {items.reduce((sum, x) => sum + (Number(x.weight) || 0), 0)}%</p><div className="flex flex-wrap gap-2"><button type="button" className={button} disabled={saving} onClick={() => setItems([...items, { ...blankItem(), weight: '' }])}>{t.add}</button><button className={primary} disabled={saving}>{saving ? t.saving : t.save}</button><button type="button" className={button} disabled={saving} onClick={() => setForm(null)}>{t.cancel}</button></div></form>}
    {form === 'assign' && <form onSubmit={assign} className="space-y-4 rounded-xl border border-slate-300 bg-white p-4 dark:border-slate-600 dark:bg-slate-900"><h2 className="text-lg font-semibold">{t.assign}</h2>{(!templates.some(x => x.is_active) || !assignees.length) && <p>{t.noOptions}</p>}<div className="grid gap-3 sm:grid-cols-2"><label>{t.employee}<select required disabled={saving} aria-invalid={invalid === 'assign'} aria-describedby={invalid === 'assign' ? 'kpi-error' : undefined} className={control} value={employeeId} onChange={e => setEmployeeId(e.target.value)}><option value="">—</option>{assignees.map(x => <option key={x.id} value={x.id}>{displayName(x.full_name_ru, x.full_name_ky, x.full_name_zh)} · {x.position}</option>)}</select></label><label>{t.template}<select required disabled={saving} aria-invalid={invalid === 'assign'} aria-describedby={invalid === 'assign' ? 'kpi-error' : undefined} className={control} value={templateId} onChange={e => { setTemplateId(e.target.value); const selectedTemplate = templates.find(x => x.id === Number(e.target.value)); setPeriod(selectedTemplate?.cycle === 'quarter' ? '1' : '01'); }}><option value="">—</option>{templates.filter(x => x.is_active).map(x => <option key={x.id} value={x.id}>{x.name} · {x.position_code} · {cycleLabel(x.cycle)}</option>)}</select></label><label>{t.year}<input required type="number" min="2000" max="2100" className={control} value={assignYear} onChange={e => setAssignYear(e.target.value)} /></label>{chosenTemplate?.cycle !== 'year' && <label>{t.period}<select className={control} value={period} onChange={e => setPeriod(e.target.value)}>{Array.from({length:chosenTemplate?.cycle === 'quarter' ? 4 : 12},(_, n) => String(n + 1).padStart(chosenTemplate?.cycle === 'quarter' ? 1 : 2, '0')).map(p => <option key={p} value={p}>{p}</option>)}</select></label>}</div><div className="flex gap-2"><button className={primary} disabled={saving || !templates.some(x => x.is_active) || !assignees.length}>{saving ? t.saving : t.assign}</button><button type="button" className={button} disabled={saving} onClick={() => setForm(null)}>{t.cancel}</button></div></form>}
    {view !== 'templates' && <><fieldset className="flex flex-wrap gap-3"><legend className="mb-2 text-sm font-medium">{t.filters}</legend><label className="w-32 text-sm">{t.year}<input type="number" min="2000" max="2100" disabled={saving} className={control} value={year} onChange={e => { setYear(e.target.value); setOffset(0); }} /></label><label className="min-w-48 text-sm">{t.status}<select disabled={saving} className={control} value={status} onChange={e => { setStatus(e.target.value); setOffset(0); }}><option value="">{t.all}</option>{statuses.map(s => <option key={s} value={s}>{statusLabel(s)}</option>)}</select></label></fieldset><div aria-busy={loading}>{loading ? <p role="status">{t.loading}</p> : tasks.length === 0 ? <p>{view === 'archive' ? t.emptyArchive : year || status ? t.emptyFiltered : t.empty}</p> : <>
      <p className="hidden text-xs text-slate-600 dark:text-slate-300 sm:block lg:hidden">{t.scroll}</p>
      <div className="hidden overflow-x-auto sm:block"><table className="w-full text-left text-sm"><caption className="sr-only">{view === 'archive' ? t.archive : t.evaluations}</caption><thead><tr>{[t.employee,t.template,t.period,t.status,t.self,t.manager,t.final,t.action].map((label, index) => <th scope="col" key={index} className="border-b border-slate-300 p-3 dark:border-slate-600">{label}</th>)}</tr></thead><tbody>{tasks.map(task => <tr key={task.id} className="border-b border-slate-200 dark:border-slate-700"><td className="p-3">{displayName(task.employee_name_ru,task.employee_name_ky,task.employee_name_zh)}</td><td className="p-3">{task.template_name}<span className="block text-xs text-slate-600 dark:text-slate-300">{task.position_code}</span></td><td className="p-3 whitespace-nowrap">{task.year} · {cycleLabel(task.cycle)} {task.cycle !== 'year' ? task.period : ''}</td><td className="p-3">{statusLabel(task.status)}</td><td className="p-3">{formatScore(task.self_score)}</td><td className="p-3">{formatScore(task.manager_score)}</td><td className="p-3">{formatScore(task.final_score)}</td><td className="p-3"><button className={button} disabled={saving} onClick={event => { openTrigger.current = event.currentTarget; setSelected(task); setScore(''); setComments(blankComments()); setForm(null); }}>{t.open}</button></td></tr>)}</tbody></table></div>
      <div className="space-y-3 sm:hidden">{tasks.map(task => <article key={task.id} className="space-y-3 rounded-lg border border-slate-300 p-4 dark:border-slate-600"><h2 className="font-semibold">{displayName(task.employee_name_ru,task.employee_name_ky,task.employee_name_zh)}</h2><dl className="grid grid-cols-2 gap-2 text-sm">{[[t.template,task.template_name],[t.period,`${task.year} · ${cycleLabel(task.cycle)} ${task.cycle === 'year' ? '' : task.period}`],[t.status,statusLabel(task.status)],[t.self,formatScore(task.self_score)],[t.manager,formatScore(task.manager_score)],[t.final,formatScore(task.final_score)]].map(([key,value]) => <div key={key} className="col-span-2 grid grid-cols-2 gap-2"><dt className="text-slate-600 dark:text-slate-300">{key}</dt><dd className="break-words">{value}</dd></div>)}</dl><button className={button} disabled={saving} onClick={event => { openTrigger.current = event.currentTarget; setSelected(task); setScore(''); setComments(blankComments()); setForm(null); }}>{t.open}</button></article>)}</div>
      <div className="mt-4 flex flex-wrap items-center gap-3"><button className={button} disabled={saving || offset === 0} onClick={() => { setOffset(Math.max(0,offset - 20)); setSelected(null); }}>{t.previous}</button><span className="text-sm">{t.shown} {offset + 1}–{offset + tasks.length} {t.of} {count}</span><button className={button} disabled={saving || offset + tasks.length >= count} onClick={() => { setOffset(offset + 20); setSelected(null); }}>{t.next}</button></div>
    </>}</div></>}
    {view === 'templates' && <div className="space-y-3">{!templates.length ? <p>{t.emptyTemplates}</p> : templates.map(template => <article key={template.id} className="rounded-lg border border-slate-300 bg-white p-4 dark:border-slate-600 dark:bg-slate-900"><h2 className="break-words font-semibold">{template.name}</h2><p className="mt-1 text-sm text-slate-600 dark:text-slate-300">{template.position_code} · {cycleLabel(template.cycle)}</p><ul className="mt-3 space-y-2">{template.items.map((item,index) => <li key={item.id || index} className="flex justify-between gap-4 text-sm"><span>{displayName(item.name_ru,item.name_ky,item.name_zh)}</span><span>{item.weight}%</span></li>)}</ul></article>)}</div>}
    {selected && <section aria-labelledby="kpi-details" className="space-y-4 rounded-xl border border-slate-300 bg-white p-4 dark:border-slate-600 dark:bg-slate-900"><div className="flex items-center justify-between gap-4"><h2 ref={detailsHeading} tabIndex={-1} id="kpi-details" className="min-w-0 break-words text-lg font-semibold focus-visible:outline-2 focus-visible:outline-blue-600">{t.details}: {displayName(selected.employee_name_ru,selected.employee_name_ky,selected.employee_name_zh)}</h2><button className={button} disabled={saving} onClick={() => { setSelected(null); openTrigger.current?.focus(); }}>{t.cancel}</button></div><p className="break-words">{selected.template_name} · {selected.year} · {cycleLabel(selected.cycle)} {selected.cycle === 'year' ? '' : selected.period}</p><ol aria-label={t.progress} className="grid gap-2 text-sm sm:grid-cols-4">{statuses.map((s,index) => <li key={s} aria-current={selected.status === s ? 'step' : undefined} className={`rounded border p-3 ${selected.status === s ? 'border-blue-700 bg-blue-50 dark:bg-blue-950' : 'border-slate-300 dark:border-slate-600'}`}>{index + 1}. {statusLabel(s)}{s === 'senior_review' && selected.status === 'confirmed' && !selected.reviewed_at ? ` · ${t.unknown}` : ''}</li>)}</ol><dl className="grid grid-cols-2 gap-3 text-sm sm:grid-cols-3">{[[t.self,formatScore(selected.self_score)],[t.manager,formatScore(selected.manager_score)],[t.final,formatScore(selected.final_score)],[t.acknowledged,selected.acknowledged_at ? formatDate(selected.acknowledged_at) : t.pending],[t.archived,selected.archived_at ? formatDate(selected.archived_at) : t.pending]].map(([key,value]) => <div key={key}><dt className="text-slate-600 dark:text-slate-300">{key}</dt><dd className="mt-1 font-medium">{value}</dd></div>)}</dl>
      {(selected.allowed_actions.includes('self_score') || selected.allowed_actions.includes('manager_score')) && <form onSubmit={scoreTask} className="space-y-3 border-t border-slate-300 pt-4 dark:border-slate-600"><p className="text-sm">{t.scoreHelp}</p><label className="block max-w-xs">{t.score}<input required disabled={saving} aria-invalid={invalid === 'score'} aria-describedby={invalid === 'score' ? 'kpi-error' : undefined} type="number" min="0" max="100" step="0.01" className={control} value={score} onChange={e => setScore(e.target.value)} /></label>{commentFields}<button disabled={saving} className={primary}>{saving ? t.saving : selected.allowed_actions.includes('self_score') ? t.sendSelf : t.sendManager}</button></form>}
      {selected.allowed_actions.includes('review') && <div className="space-y-3 border-t border-slate-300 pt-4 dark:border-slate-600"><h3 className="font-medium">{t.senior}</h3>{commentFields}<div className="flex flex-wrap gap-2"><button className={primary} disabled={saving} onClick={() => review('approve')}>{saving ? t.saving : t.approve}</button><button className={button} disabled={saving} onClick={() => review('return')}>{t.return}</button></div></div>}
      {selected.allowed_actions.includes('acknowledge') && <div className="space-y-3 border-t border-slate-300 pt-4 dark:border-slate-600"><p>{t.acknowledgeHelp}</p><button className={primary} disabled={saving} onClick={() => void run(() => api.acknowledgeKpiTask(selected.id))}>{saving ? t.saving : t.acknowledge}</button></div>}
      {selected.allowed_actions.includes('archive') && <button className={button} disabled={saving} onClick={() => void run(() => api.archiveKpiTask(selected.id))}>{t.archiveAction}</button>}
      <div className="space-y-3 border-t border-slate-300 pt-4 dark:border-slate-600">{(['self','manager','review'] as const).map(stage => { const c = selected.comments?.[stage]; return c && Object.values(c).some(Boolean) ? <div key={stage}><h3 className="font-medium">{stage === 'self' ? t.self : stage === 'manager' ? t.manager : t.senior}</h3><p className="break-words whitespace-pre-wrap text-sm">{displayName(c.ru,c.ky,c.zh)}</p></div> : null; })}<h3 className="font-semibold">{t.history}</h3>{!selected.history?.length ? <p className="mt-2 text-sm">{t.noHistory}</p> : <ol className="mt-3 space-y-3">{selected.history.map(event => <li key={event.id} className="text-sm"><p className="font-medium">{event.actor_name} · {formatDate(event.created_at)}</p><p>{historyLabel(event.action,t)}</p>{(() => { const c = event.new_data?.comments as KpiComments | undefined; return c && Object.values(c).some(Boolean) ? <p className="mt-1 break-words whitespace-pre-wrap">{displayName(c.ru,c.ky,c.zh)}</p> : null; })()}</li>)}</ol>}</div>
    </section>}
  </section>;
}

function historyLabel(action: string, t: typeof kpiTranslations.ru) {
  const actions: Record<string,string> = { 'kpi.assigned':t.assign, 'kpi.review_approve':t.approve, 'kpi.review_return':t.return, 'kpi.task.created':t.assign, 'kpi.created':t.assign, 'kpi.self_scored':t.self, 'kpi.manager_scored':t.manager, 'kpi.reviewed':t.senior, 'kpi.approved':t.approve, 'kpi.returned':t.return, 'kpi.acknowledged':t.acknowledged, 'kpi.archived':t.archived };
  return actions[action] || t.details;
}
