# Проверка online WMS

`wms-smoke.cjs` проверяет пять вкладок для четырёх языков, светлой/тёмной темы
и ширин 360/1440. Проверяются JavaScript-ошибки, переполнение и выбранные
правила axe. `wms-flows.cjs` проверяет формы, проведение, возврат фокуса,
конфликт первичного документа и отзыв доступа.

Сценарии используют mock API: они не отправляют складские документы в backend.
Для прав и изменения остатков запускать также Django-тесты.

## Повторение

Установить инструменты отдельно от зависимостей приложения:

```bash
npm install --prefix /tmp/yrys-ui-check --no-audit --no-fund playwright axe-core
/tmp/yrys-ui-check/node_modules/.bin/playwright install chromium
```

В отдельном терминале из `frontend` запустить:

```bash
npm run dev -- --hostname 127.0.0.1 --port 3015
```

Из корня репозитория:

```bash
PLAYWRIGHT_MODULE=/tmp/yrys-ui-check/node_modules/playwright \
AXE_MODULE=/tmp/yrys-ui-check/node_modules/axe-core/axe.min.js \
node docs/verification/wms-smoke.cjs

PLAYWRIGHT_MODULE=/tmp/yrys-ui-check/node_modules/playwright \
AXE_MODULE=/tmp/yrys-ui-check/node_modules/axe-core/axe.min.js \
node docs/verification/wms-flows.cjs
```

Другой адрес frontend задаётся переменной `UI_BASE_URL`. Скриншоты и JSON
матрицы записываются в `/tmp/yrys-ui-check`. Успешная автоматическая проверка
не заменяет ручную проверку доступности и полноценную приёмку требований ТЗ.

31.10.2026: матрица 16 сочетаний/80 проверок — успешна; все flow-сценарии —
успешны. Полный Django-набор: 85 тестов, `OK (skipped=1)` на SQLite.
