'use client';

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { User, LanguageCode, AttendanceStatus } from '@/types';
import { translations } from '@/lib/i18n';
import { api } from '@/lib/api';
import {
  MapPin,
  LogIn,
  LogOut,
  Coffee,
  CheckCircle2,
  AlertTriangle,
  ShieldCheck,
} from 'lucide-react';

interface AttendanceWidgetProps {
  currentUser: User | null;
  lang: LanguageCode;
  onStatusChange?: () => void;
}

export const AttendanceWidget: React.FC<AttendanceWidgetProps> = ({
  currentUser,
  lang,
  onStatusChange,
}) => {
  const t = translations[lang] || translations.ru;
  const [status, setStatus] = useState<AttendanceStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const [geoCoords, setGeoCoords] = useState<{ latitude: number; longitude: number; accuracy?: number } | null>(null);
  const [distanceToOffice, setDistanceToOffice] = useState<number | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Modals
  const [showLeaveModal, setShowLeaveModal] = useState(false);
  const [leaveType, setLeaveType] = useState<'lunch' | 'business' | 'personal' | 'other'>('lunch');
  const [leaveReason, setLeaveReason] = useState('');
  const [leaveComment, setLeaveComment] = useState('');

  const [showConsentModal, setShowConsentModal] = useState(false);
  const trackerIntervalRef = useRef<NodeJS.Timeout | null>(null);

  // Periodic location updater for background tracking
  useEffect(() => {
    if (status?.is_consent_granted && status?.is_checked_in) {
      trackerIntervalRef.current = setInterval(() => {
        if ('geolocation' in navigator) {
          navigator.geolocation.getCurrentPosition(
            async (pos) => {
              try {
                const res = await api.sendLocationLog({
                  latitude: pos.coords.latitude,
                  longitude: pos.coords.longitude,
                  accuracy_meters: pos.coords.accuracy,
                  source: 'web',
                });
                if (res.needs_absence_prompt) {
                  setShowLeaveModal(true);
                }
              } catch {
                // silent
              }
            },
            () => {},
            { enableHighAccuracy: false, timeout: 10000 }
          );
        }
      }, 5 * 60 * 1000); // every 5 minutes
    } else {
      if (trackerIntervalRef.current) clearInterval(trackerIntervalRef.current);
    }

    return () => {
      if (trackerIntervalRef.current) clearInterval(trackerIntervalRef.current);
    };
  }, [status?.is_consent_granted, status?.is_checked_in]);

  const obtainLocation = useCallback(() => {
    if (typeof window !== 'undefined' && 'geolocation' in navigator) {
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          const coords = {
            latitude: pos.coords.latitude,
            longitude: pos.coords.longitude,
            accuracy: pos.coords.accuracy,
          };
          setGeoCoords(coords);
        },
        (err) => {
          console.warn('Geolocation warning:', err.message);
        },
        { enableHighAccuracy: true, timeout: 8000 }
      );
    }
  }, []);

  const calculateDistance = useCallback((coords: { latitude: number; longitude: number }, office: { latitude: number; longitude: number }) => {
    const R = 6371000;
    const dLat = ((office.latitude - coords.latitude) * Math.PI) / 180;
    const dLon = ((office.longitude - coords.longitude) * Math.PI) / 180;
    const a =
      Math.sin(dLat / 2) * Math.sin(dLat / 2) +
      Math.cos((coords.latitude * Math.PI) / 180) *
        Math.cos((office.latitude * Math.PI) / 180) *
        Math.sin(dLon / 2) *
        Math.sin(dLon / 2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    const d = Math.round(R * c);
    setDistanceToOffice(d);
  }, []);

  const loadStatus = useCallback(async () => {
    try {
      const res = await api.getAttendanceStatus();
      setStatus(res);
    } catch (err: any) {
      console.error(err);
    }
  }, []);

  useEffect(() => {
    if (currentUser) {
      loadStatus();
      obtainLocation();
    }
  }, [currentUser, loadStatus, obtainLocation]);

  useEffect(() => {
    if (geoCoords && status?.office) {
      calculateDistance(geoCoords, status.office);
    }
  }, [geoCoords, status?.office, calculateDistance]);

  const handleCheckIn = async () => {
    try {
      setLoading(true);
      setErrorMessage(null);

      // Refresh GPS
      let currentCoords = geoCoords;
      if ('geolocation' in navigator) {
        try {
          const pos: any = await new Promise((resolve, reject) => {
            navigator.geolocation.getCurrentPosition(resolve, reject, { enableHighAccuracy: true, timeout: 8000 });
          });
          currentCoords = {
            latitude: pos.coords.latitude,
            longitude: pos.coords.longitude,
            accuracy: pos.coords.accuracy,
          };
          setGeoCoords(currentCoords);
        } catch {
          // Coords fallback
        }
      }

      await api.checkIn({
        latitude: currentCoords?.latitude,
        longitude: currentCoords?.longitude,
        accuracy_meters: currentCoords?.accuracy,
        office_id: status?.office?.id,
      });

      await loadStatus();
      if (onStatusChange) onStatusChange();
    } catch (err: any) {
      setErrorMessage(err.message || 'Ошибка отметки прихода');
    } finally {
      setLoading(false);
    }
  };

  const handleCheckOut = async () => {
    try {
      setLoading(true);
      setErrorMessage(null);

      await api.checkOut({
        latitude: geoCoords?.latitude,
        longitude: geoCoords?.longitude,
        accuracy_meters: geoCoords?.accuracy,
        office_id: status?.office?.id,
      });

      await loadStatus();
      if (onStatusChange) onStatusChange();
    } catch (err: any) {
      setErrorMessage(err.message || 'Ошибка отметки ухода');
    } finally {
      setLoading(false);
    }
  };

  const handleLeave = async () => {
    try {
      setLoading(true);
      setErrorMessage(null);
      await api.leaveAbsence({
        absence_type: leaveType,
        reason: leaveReason,
        comment: leaveComment,
      });
      setShowLeaveModal(false);
      setLeaveReason('');
      setLeaveComment('');
      await loadStatus();
      if (onStatusChange) onStatusChange();
    } catch (err: any) {
      setErrorMessage(err.message || 'Ошибка фиксации отлучки');
    } finally {
      setLoading(false);
    }
  };

  const handleResume = async () => {
    try {
      setLoading(true);
      setErrorMessage(null);
      await api.resumeAbsence();
      await loadStatus();
      if (onStatusChange) onStatusChange();
    } catch (err: any) {
      setErrorMessage(err.message || 'Ошибка фиксации возврата');
    } finally {
      setLoading(false);
    }
  };

  const handleGrantConsent = async (grant: boolean) => {
    try {
      setLoading(true);
      await api.setConsent({
        is_granted: grant,
        consent_version: '1.0',
        consent_text: 'Согласие на сбор геопозиции в рабочее время с 90-дневным сроком хранения',
      });
      setShowConsentModal(false);
      await loadStatus();
    } catch (err: any) {
      alert(err.message);
    } finally {
      setLoading(false);
    }
  };

  if (!currentUser) return null;

  const isCheckedIn = status?.is_checked_in;
  const activeBreak = status?.active_break;
  const office = status?.office;
  const radius = office?.radius_meters || 100;
  const isWithin = distanceToOffice !== null ? distanceToOffice <= radius : true;

  return (
    <div className="w-full bg-white dark:bg-slate-900 border-b border-slate-200 dark:border-slate-800 shadow-sm transition-colors">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-2.5 flex flex-wrap items-center justify-between gap-3 text-xs sm:text-sm">
        {/* Left: Live Status & Office distance */}
        <div className="flex items-center flex-wrap gap-2.5">
          <div className="flex items-center gap-1.5 font-bold">
            <span className="flex h-2.5 w-2.5 relative">
              <span
                className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${
                  isCheckedIn ? (activeBreak ? 'bg-amber-400' : 'bg-emerald-400') : 'bg-slate-400'
                }`}
              />
              <span
                className={`relative inline-flex rounded-full h-2.5 w-2.5 ${
                  isCheckedIn ? (activeBreak ? 'bg-amber-500' : 'bg-emerald-500') : 'bg-slate-400'
                }`}
              />
            </span>
            <span className="text-black dark:text-white">
              {isCheckedIn
                ? activeBreak
                  ? `${t.onBreak}: ${
                      activeBreak.absence_type === 'lunch'
                        ? t.lunch
                        : activeBreak.absence_type === 'business'
                        ? t.businessBreak
                        : activeBreak.absence_type === 'personal'
                        ? t.personalBreak
                        : t.otherBreak
                    }`
                  : t.inOffice
                : t.notCheckedIn}
            </span>
          </div>

          {office && (
            <div className="hidden md:flex items-center gap-1 text-[11px] font-medium text-slate-700 dark:text-slate-300 bg-slate-100 dark:bg-slate-800 px-2 py-0.5 rounded-lg border border-slate-200 dark:border-slate-700">
              <MapPin className="w-3 h-3 text-blue-600" />
              <span>{office.name}</span>
              {distanceToOffice !== null && (
                <span className={`font-bold ml-1 ${isWithin ? 'text-emerald-700 dark:text-emerald-400' : 'text-rose-600 dark:text-rose-400'}`}>
                  ({distanceToOffice}м / {radius}м)
                </span>
              )}
            </div>
          )}

          {/* Background Tracking Badge / Consent */}
          <button
            onClick={() => setShowConsentModal(true)}
            className={`flex items-center gap-1 text-[11px] font-semibold px-2 py-0.5 rounded-lg border transition ${
              status?.is_consent_granted
                ? 'bg-blue-50 dark:bg-blue-950/40 text-blue-700 dark:text-blue-300 border-blue-200 dark:border-blue-800 hover:bg-blue-100'
                : 'bg-amber-50 dark:bg-amber-950/40 text-amber-700 dark:text-amber-300 border-amber-200 dark:border-amber-800 hover:bg-amber-100'
            }`}
            title="Электронное согласие на геолокацию в рабочее время"
          >
            <ShieldCheck className="w-3 h-3" />
            <span className="hidden sm:inline">
              {status?.is_consent_granted ? t.consentGranted : t.locationConsent}
            </span>
          </button>
        </div>

        {/* Center / Right: Action Buttons */}
        <div className="flex items-center gap-2">
          {/* Check In Button */}
          {!isCheckedIn ? (
            <button
              onClick={handleCheckIn}
              disabled={loading}
              className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-600 text-white font-bold hover:from-emerald-500 hover:to-teal-500 shadow-sm shadow-emerald-500/20 active:scale-95 transition"
            >
              <LogIn className="w-3.5 h-3.5" />
              <span>{t.checkIn}</span>
            </button>
          ) : (
            <>
              {/* Intra-day absence: Leave / Resume */}
              {!activeBreak ? (
                <button
                  onClick={() => setShowLeaveModal(true)}
                  disabled={loading}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-amber-50 dark:bg-amber-950/50 text-amber-900 dark:text-amber-200 border border-amber-300 dark:border-amber-800 font-bold hover:bg-amber-100 dark:hover:bg-amber-900/60 active:scale-95 transition"
                >
                  <Coffee className="w-3.5 h-3.5 text-amber-600" />
                  <span>{t.leaveBreak}</span>
                </button>
              ) : (
                <button
                  onClick={handleResume}
                  disabled={loading}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-indigo-50 dark:bg-indigo-950/50 text-indigo-900 dark:text-indigo-200 border border-indigo-300 dark:border-indigo-800 font-bold hover:bg-indigo-100 dark:hover:bg-indigo-900/60 active:scale-95 transition"
                >
                  <CheckCircle2 className="w-3.5 h-3.5 text-indigo-600" />
                  <span>{t.resumeBreak}</span>
                </button>
              )}

              {/* Check Out Button */}
              <button
                onClick={handleCheckOut}
                disabled={loading}
                className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl bg-rose-600 hover:bg-rose-500 text-white font-bold shadow-sm shadow-rose-500/20 active:scale-95 transition"
              >
                <LogOut className="w-3.5 h-3.5" />
                <span>{t.checkOut}</span>
              </button>
            </>
          )}
        </div>
      </div>

      {/* Reminder Alert Banner */}
      {status?.forgot_checkout_reminder && (
        <div className="bg-amber-500 text-white px-4 py-1.5 text-center text-xs font-bold flex items-center justify-center gap-2">
          <AlertTriangle className="w-4 h-4" />
          <span>Напоминание: рабочий день подошёл к концу. Не забудьте нажать «Ушёл»!</span>
        </div>
      )}

      {/* Error Message */}
      {errorMessage && (
        <div className="bg-rose-50 dark:bg-rose-950/80 border-t border-rose-200 dark:border-rose-900 px-4 py-2 text-xs font-semibold text-rose-800 dark:text-rose-200 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-rose-600 flex-shrink-0" />
            <span>{errorMessage}</span>
          </div>
          <button onClick={() => setErrorMessage(null)} className="font-bold underline ml-2">
            OK
          </button>
        </div>
      )}

      {/* Leave Modal */}
      {showLeaveModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div className="bg-white dark:bg-slate-900 rounded-2xl max-w-md w-full p-6 shadow-2xl border border-slate-200 dark:border-slate-800 space-y-4 animate-in fade-in zoom-in-95">
            <div className="flex items-center gap-2.5 pb-2 border-b border-slate-200 dark:border-slate-800">
              <div className="h-9 w-9 rounded-xl bg-amber-100 dark:bg-amber-950/60 flex items-center justify-center text-amber-600">
                <Coffee className="w-5 h-5" />
              </div>
              <h3 className="text-base font-bold text-black dark:text-white">
                {t.leaveBreak}
              </h3>
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-1.5">
                Причина отлучки
              </label>
              <div className="grid grid-cols-2 gap-2">
                {[
                  { id: 'lunch', label: t.lunch },
                  { id: 'business', label: t.businessBreak },
                  { id: 'personal', label: t.personalBreak },
                  { id: 'other', label: t.otherBreak },
                ].map((item) => (
                  <button
                    key={item.id}
                    type="button"
                    onClick={() => setLeaveType(item.id as any)}
                    className={`py-2 px-3 text-xs font-bold rounded-xl border text-center transition ${
                      leaveType === item.id
                        ? 'bg-blue-600 text-white border-blue-600 shadow-sm'
                        : 'bg-slate-50 dark:bg-slate-800 text-slate-700 dark:text-slate-200 border-slate-300 dark:border-slate-700 hover:bg-slate-100'
                    }`}
                  >
                    {item.label}
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-1">
                Комментарий / Куда направляетесь (необязательно)
              </label>
              <textarea
                value={leaveComment}
                onChange={(e) => setLeaveComment(e.target.value)}
                placeholder="Например: Встреча с клиентом или Обед в столовой..."
                className="w-full text-xs rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 p-2.5 text-black dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                rows={2}
              />
            </div>

            <div className="flex justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={() => setShowLeaveModal(false)}
                className="px-4 py-2 text-xs font-bold rounded-xl border border-slate-300 dark:border-slate-700 text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800"
              >
                {t.cancel}
              </button>
              <button
                type="button"
                onClick={handleLeave}
                disabled={loading}
                className="px-4 py-2 text-xs font-bold rounded-xl bg-blue-600 hover:bg-blue-500 text-white shadow-sm"
              >
                Подтвердить
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Consent Modal */}
      {showConsentModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div className="bg-white dark:bg-slate-900 rounded-2xl max-w-lg w-full p-6 shadow-2xl border border-slate-200 dark:border-slate-800 space-y-4 animate-in fade-in zoom-in-95">
            <div className="flex items-center gap-2.5 pb-2 border-b border-slate-200 dark:border-slate-800">
              <div className="h-9 w-9 rounded-xl bg-blue-100 dark:bg-blue-950/60 flex items-center justify-center text-blue-600">
                <ShieldCheck className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-base font-bold text-black dark:text-white">
                  {t.locationConsent}
                </h3>
                <p className="text-[11px] text-slate-500">Политика безопасности и конфиденциальности (ТЗ п. 4.9)</p>
              </div>
            </div>

            <div className="text-xs text-slate-700 dark:text-slate-300 space-y-2 leading-relaxed bg-slate-50 dark:bg-slate-800/60 p-3.5 rounded-xl border border-slate-200 dark:border-slate-700">
              <p className="font-semibold text-black dark:text-white">Правила учёта местоположения:</p>
              <ul className="list-disc list-inside space-y-1">
                <li>Отслеживание ведётся <strong>только в рабочее время</strong> по установленному графику.</li>
                <li>Вне рабочего времени и выходные приложение координаты <strong>не собирает</strong>.</li>
                <li>Координаты собираются в экономном режиме (раз в 5–10 мин) для сохранения заряда батареи.</li>
                <li>Срок хранения геоданных строго ограничен <strong>90 днями</strong>, после чего они автоматически удаляются.</li>
                <li>Вы всегда можете отозвать данное согласие в своём профиле.</li>
              </ul>
            </div>

            <div className="flex items-center justify-between pt-2">
              {status?.is_consent_granted ? (
                <button
                  type="button"
                  onClick={() => handleGrantConsent(false)}
                  disabled={loading}
                  className="px-4 py-2 text-xs font-bold rounded-xl text-rose-600 border border-rose-200 hover:bg-rose-50"
                >
                  {t.revokeConsent}
                </button>
              ) : (
                <div />
              )}

              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => setShowConsentModal(false)}
                  className="px-4 py-2 text-xs font-bold rounded-xl border border-slate-300 dark:border-slate-700 text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800"
                >
                  Закрыть
                </button>
                {!status?.is_consent_granted && (
                  <button
                    type="button"
                    onClick={() => handleGrantConsent(true)}
                    disabled={loading}
                    className="px-4 py-2 text-xs font-bold rounded-xl bg-blue-600 hover:bg-blue-500 text-white shadow-sm"
                  >
                    {t.grantConsent}
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
