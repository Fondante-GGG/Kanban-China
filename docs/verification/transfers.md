# Браузерная проверка перемещений

Инструменты устанавливаются отдельно от зависимостей приложения, как описано
в `warehouse.md`. Запустить frontend на `127.0.0.1:3015`, затем из корня проекта:

```bash
export PLAYWRIGHT_MODULE=/tmp/yrys-ui-check/node_modules/playwright
export AXE_MODULE=/tmp/yrys-ui-check/node_modules/axe-core/axe.min.js
node docs/verification/transfers-smoke.cjs
node docs/verification/transfers-flows.cjs
node docs/verification/transfers-async.cjs
```

Другой адрес задаётся через `UI_BASE_URL`. Все API-ответы подменены тестовыми:
сценарии не создают складские документы в рабочей базе. Серверные права,
остатки, аудит и идемпотентность отдельно проверяются Django-тестами.

Результаты 31.10.2026:

- Матрица 16 сочетаний: четыре языка, две темы, 360/1440 px. Открытые детали
  входящего перемещения — без JavaScript-ошибок, переполнения и обнаруженных
  нарушений axe WCAG 2 A/AA и 2.1 AA. JSON и скриншоты: `/tmp/yrys-transfer-check`.
- Основной маршрут, восемь POST/PATCH: создание с партией и ячейками, причина
  возврата, неизменяемость маршрута при исправлении, независимое утверждение,
  подтверждения отправки/получения и отзыв доступа — `PASS`.
- Асинхронные проверки: запоздалые детали после смены фильтра, 403, старый
  ответ каталога после отзыва прав, повтор exact-ID после 500 вне первой
  страницы списка — `PASS`.
- Полный backend: `DJANGO_DEBUG=true backend/venv/bin/python backend/manage.py test backend.tests --noinput`
  — 95 тестов, `OK (skipped=2)`; PostgreSQL-конкурентность пропущена на SQLite.

Автоматическая матрица не является полной сертификацией доступности.
Проверка с подменённым API не заменяет реальный end-to-end пилот.
