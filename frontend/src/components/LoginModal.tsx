'use client';

import React, { useState } from 'react';
import { api } from '@/lib/api';
import { User, LanguageCode } from '@/types';
import { translations } from '@/lib/i18n';
import { Kanban, Lock, Mail, ArrowRight } from 'lucide-react';

interface LoginModalProps {
  onSuccess: (user: User) => void;
  lang: LanguageCode;
}

export const LoginModal: React.FC<LoginModalProps> = ({ onSuccess, lang }) => {
  const t = translations[lang] || translations.ru;
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.trim() || !password) return;
    try {
      setLoading(true);
      setError(null);
      const res = await api.login(email.trim(), password);
      onSuccess(res.user);
    } catch (err: any) {
      setError(err.message || 'Ошибка входа');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/70 backdrop-blur-md animate-in fade-in">
      <div className="w-full max-w-md rounded-3xl bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-800 shadow-2xl p-6 sm:p-8 space-y-6">
        {/* Brand Header */}
        <div className="text-center space-y-2">
          <div className="inline-flex h-12 w-12 rounded-2xl bg-gradient-to-tr from-blue-600 via-indigo-600 to-violet-600 items-center justify-center text-white shadow-lg shadow-blue-500/30">
            <Kanban className="w-6 h-6" />
          </div>
          <h2 className="text-2xl font-black text-black dark:text-white tracking-tight">
            {t.appName}
          </h2>
          <p className="text-xs text-slate-800 dark:text-slate-300 font-semibold max-w-xs mx-auto">
            Канбан-система управления задачами с ролевым доступом и машинным переводом
          </p>
        </div>

        {error && (
          <div className="p-3 rounded-xl bg-rose-50 dark:bg-rose-950/50 border border-rose-300 dark:border-rose-900 text-xs text-rose-700 dark:text-rose-400 font-bold text-center">
            {error}
          </div>
        )}

        {/* Login Form */}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="text-xs font-bold text-black dark:text-slate-100 uppercase tracking-wider block mb-1">
              {t.email}
            </label>
            <div className="relative">
              <Mail className="w-4 h-4 text-black dark:text-slate-300 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="name@company.com"
                className="w-full pl-9 pr-3 py-2.5 text-xs sm:text-sm font-semibold rounded-xl border border-slate-400 dark:border-slate-700 bg-white dark:bg-slate-800 text-black dark:text-white placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500/20"
                required
                autoFocus
              />
            </div>
          </div>

          <div>
            <label className="text-xs font-bold text-black dark:text-slate-100 uppercase tracking-wider block mb-1">
              {t.password}
            </label>
            <div className="relative">
              <Lock className="w-4 h-4 text-black dark:text-slate-300 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full pl-9 pr-3 py-2.5 text-xs sm:text-sm font-semibold rounded-xl border border-slate-400 dark:border-slate-700 bg-white dark:bg-slate-800 text-black dark:text-white placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500/20"
                required
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-2.5 px-4 rounded-xl bg-blue-600 hover:bg-blue-700 text-white text-xs sm:text-sm font-extrabold shadow-md shadow-blue-500/25 flex items-center justify-center gap-2 transition disabled:opacity-50"
          >
            <span>{loading ? 'Вход...' : t.login}</span>
            <ArrowRight className="w-4 h-4" />
          </button>
        </form>
      </div>
    </div>
  );
};
