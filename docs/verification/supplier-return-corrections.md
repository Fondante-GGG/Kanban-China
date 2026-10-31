# Проверка корректировок задолженности по возврату

Дата: 31.10.2026. Область — утверждённая пользователем ручная корректировка
непогашенного долга в его валюте. Источники: ТЗ Г.6/Б7.3,
[ADR-0005](../adr/0005-supplier-return-debt-corrections.md),
[API/OpenAPI](../api/supplier-return-corrections.md).

## Проверки

- Владелец backend: 13 targeted тестов, `OK (skipped=2)`, 45.949 с.
  Независимый reviewer: 12 targeted, `OK (skipped=2)` + отдельный mixed settlement
  regression, 1 тест, `OK`.
- `manage.py check`: нет замечаний; `makemigrations --check --dry-run`:
  `No changes detected`. Compileall и `git diff --check` успешны.
- OpenAPI: `python -m openapi_spec_validator docs/openapi/supplier-return-corrections.json`.
- Владелец FE и интеграция: `npm run lint && npx tsc --noEmit && npm run build`, exit0.
- Playwright + axe, mock API: 16 сочетаний RU/KY/zh-Hans/zh-Hant × светлая/тёмная
  тема × ширина360/1440. Проверены форма, итоговое подтверждение и успешный
  результат. Нет ошибок JS, переполнения и найденных axe-нарушений в summary.
- Браузерные сценарии: потерянный ответ после применения, remount очереди и точный повтор того же
  UUID/payload (один документ/одно уменьшение); загруженная read-only роль без
  действия подтверждения; превышение остатка без POST, закрытый период409 и
  исправление даты; отзыв доступа403 с удалением карточки и формы; большая сумма и уменьшение
  ровно на0.01 без потери младших разрядов.
- Найденный контраст hover primary-кнопки исправлен разделением CSS-классов;
  итоговая матрица прошла. Найденный смешанный сценарий корректировка+доплата
  исправлен: итоговый статус `settled_by_adjustment`, а чистая оплата — `paid`.

## Воспроизведение

Backend из backend-директории в подготовленном окружении с тестовым secret/debug:

```sh
python manage.py test backend.tests.test_supplier_return_corrections
python manage.py test
python manage.py check
python manage.py makemigrations --check --dry-run
```

Frontend поднять локально на3016. Установить Playwright Chromium и axe-core во
внешнем проверочном окружении, затем из корня:

```sh
UI_BASE_URL=http://127.0.0.1:3016 \
PLAYWRIGHT_MODULE=/path/to/node_modules/playwright \
AXE_MODULE=/path/to/node_modules/axe-core/axe.min.js \
node docs/verification/supplier-return-corrections.cjs
```

Результаты: `/tmp/yrys-return-corrections-check/results.json` (21 запись).
Существующий supplier-returns-smoke helper получил только необязательный hook
подготовки mock-маршрутов до навигации; прежние вызовы совместимы.

## Ограничения и внедрение

Браузерные сценарии используют mock API; реальные остатки, права, деньги и
откаты проверяются отдельными Django-тестами. Реальная E2E-приёмка и полная
сертификация accessibility не заявляются. SQLite не подтверждает PostgreSQL
row locks; две новые реальные contention-проверки пропущены на SQLite.

UUID незавершённого UI-запроса хранится только в памяти вкладки, привязан к
текущей пользовательской сессии и переживает remount карточки. Полная перезагрузка
теряет его. После неё перед новой операцией требуется проверить историю;
без сохранённого ключа невозможно гарантировать идемпотентный повтор старого
запроса. Суммы/ключи не записываются в browser persistent storage.

Миграция0049 подготовлена, к рабочей базе не применена. Перед использованием
нужны последовательные миграции и существующие права finance.payable.read/manage.
Deploy, commit/push и операции с рабочими денежными данными не выполнялись.
Возврат денег/FX/полный план счетов/общая сумма требования и закрытие рассмотрения
остаются отдельными задачами. Parent review остаётся pending, отдельные документы
корректировок проведены и неизменяемы.

Финальный полный backend-прогон: **144 теста**, 241.468с, `OK (skipped=7)`;
137 выполнены, семь PostgreSQL concurrency-проверок пропущены на SQLite.
Включено исправление смешанного погашения долга корректировкой и платежом.

Независимое ревью CR-01: **APPROVED** для ручной корректировки открытого долга;
открытых обязательных замечаний нет. Возврат денег, FX и закрытие рассмотрения
остаются вне принятого этапа.
