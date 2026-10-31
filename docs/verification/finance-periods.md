# Проверка закрытия финансового месяца

Дата:31.10.2026. Утверждённые даты/правила — ADR-0006, контракт/OpenAPI —
[finance-periods](../api/finance-periods.md). Изменения выполнялись в отдельных
рабочих копиях от снимка primary с предыдущими несохранёнными в commit этапами.
Рабочие финансовые данные и миграции не изменялись.

## Проверки интерфейса

Playwright+axe на mock API:16 сочетаний RU/KY/zh-Hans/zh-Hant × светлая/тёмная
тема × ширина360/1440. Форма→summary→подтверждение→closed metadata;
нет JS-ошибок, горизонтального переполнения и найденных axe-нарушений summary.
Ещё3сценария: потерянный ответ после фиксации закрытия с авторитетным reread
(одинPOST); read-only без закрытия; отзыв права403 с удалением12карточек.
Результаты `/tmp/yrys-period-check/results.json`:19записей.

Воспроизведение из корня с frontend на3017 и Playwright Chromium/axe-core:

```sh
UI_BASE_URL=http://127.0.0.1:3017 \
PLAYWRIGHT_MODULE=/path/to/node_modules/playwright \
AXE_MODULE=/path/to/node_modules/axe-core/axe.min.js \
node docs/verification/finance-periods.cjs
```

Mock не заменяет реальный Django/PostgreSQL E2E. Это не полная сертификацияWCAG.
Helper прежнего supplier-returns smoke теперь выбирает финансовую очередь по
доступному заголовку, а не по порядку section; axe принимает явный selector,
чтобы новая секция не заменила проверяемую прежнюю очередь.

## Backend и внедрение

Проверки выполняются на временной тестовой SQLite базе, не рабочей БД.
Реальная конкурентность row locks требует PostgreSQL; пропуски ниже не
выдаются за доказательство блокировок. API admin SQL-доступ не заменяет:
прямые shell/DB операции находятся вне HTTP-гарантии.

Команды: `python manage.py test`, targeted `backend.tests.test_finance_periods`,
`python manage.py check`, `python manage.py makemigrations --check --dry-run`,
`python -m openapi_spec_validator docs/openapi/finance-periods.json`,
`npm run lint && npx tsc --noEmit && npm run build`, `git diff --check`.
Итоговые наблюдаемые результаты дополняются после завершения прогонов.

0050 добавляет право без autoassign, основание закрытия и ограничения year/month.
Невалидные существующие year/month миграция молча не исправляет: перед внедрением
нужна отдельная проверка данных. Миграция рабочей БД не применялась. API повторного
открытия нет; rollback БД не является способом отменить закрытие. Commit/push/deploy
не выполнялись. Полное выполнение ТЗ данным этапом не заявляется.

Проверено: целевой backend38тестов, `OK(skipped=3)`,94.821с;
дополнительная историческая GET/download-проверка1тест `OK`.
Frontend lint/TypeScript/production build — exit0. Check, migration dry-run,
OpenAPI и diffcheck — успешно. 19браузерных результатов без ошибок
(16сочетаний+3сценария); API в браузере подменён mock.

Регрессия складских возвратов/финансовой очереди:32сочетания роли/языка/темы/ширины,
защищённые фото и bearer-запросы — успешно, без JS/overflow/axe нарушений.

Финальный полный backend:157тестов за265.815с, `OK(skipped=8)`.
149тестов выполнены; восемь реальных PostgreSQL-проверок конкурентности
пропущены на SQLite. Дополнительная обновлённая историческая GET/download
проверка пройдена отдельно на финальном тестовом файле; production-код
полного прогона совпадает с итоговым проверенным снимком.

Независимое ревью CR-01: **APPROVED** для закрытия месяца и защиты
перечисленных финансовых операций. Независимо13period-тестов: `OK(skipped=1)`,
15.052с; FE lint/typecheck, OpenAPI и diffcheck — успешно.
Предварительный NOT READY подготовительного снимка заменён итоговым решением.
Полная приёмка ТЗ, реальные PostgreSQL-гонки и realE2E этим не подтверждены.
