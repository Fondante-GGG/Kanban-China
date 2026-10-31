# Supplier return debt corrections

Модуль финансов монолита. Основание и граница этапа:
[ADR-0005](../adr/0005-supplier-return-debt-corrections.md).
Машиночитаемый контракт: [OpenAPI](../openapi/supplier-return-corrections.json).

## GET /api/finance/supplier-returns/{review_id}/corrections

Bearer auth; `finance.payable.read`. Рассмотрение должно относиться к проведённому
возврату. Право на склад не требуется и не выдаётся.

Параметры: `limit`/`offset` для истории, `payable_limit`/`payable_offset` для долгов.
Оба limit по умолчанию 20, диапазон 1–100; offset от 0 до 1000000000.
`q` (до 128 символов) ищет подходящие долги по ID или номеру исходной сверки.
Долги ограничены тем же поставщиком/заказом, положительным остатком и статусом
`open/partially_paid`; сортировка по ID. История новых документов — по ID убыванию.

Ответ: `review_id`, `review_status`, `corrections`, `correction_count`, `payables`,
`payable_count`, `limit`, `offset`, `payable_limit`, `payable_offset`, `can_confirm`.
`can_confirm` отражает текущее `finance.payable.manage`; сервер повторяет проверку
при POST. Долг: `id`, `supplier_id`, `purchase_order_id`, `source_type`, `source_id`,
`amount`, `outstanding_amount`, `currency`, `status`.

## POST /api/finance/supplier-returns/{review_id}/corrections

Bearer auth; `finance.payable.manage`. Все поля обязательны, неизвестные поля
запрещены. Дополнительного автоматического согласования не вводится.

```json
{
  "request_id": "c7f859ba-42fe-4f8b-9078-86a57a9b7461",
  "payable_id": 42,
  "amount": "100.25",
  "currency": "CNY",
  "posting_date": "2026-10-31",
  "document_no": "CN-2026-001",
  "reason": "Подтверждённая бухгалтером сумма корректировки"
}
```

- `request_id` — UUID ключ повторного запроса; сохранить при сетевой ошибке.
- `payable_id` — положительный integer, не строка/boolean.
- `amount` — строка положительного decimal, до 14 цифр целой части и двух
  дробных знаков; NaN/Infinity/float/exponent/скрытое округление запрещены.
- `currency` — три заглавные буквы, точно валюта выбранного долга; без FX.
- `posting_date` — существующая календарная дата строго YYYY-MM-DD в открытом периоде.
- `document_no` — непустая строка до 128 символов; `reason` — до 4000.
  Краевые пробелы удаляются; NUL запрещён.

201 создаёт документ; 200 — точный повтор ранее проведённого запроса, включая
повтор после погашения долга или закрытия периода. Нормализованные значения
`0.1` и `0.10` равны. Смена реквизитов с прежним UUID — 409.
Если результат неизвестен из-за сети, сначала повторить **тот же UUID и payload**,
не создавать новую корректировку под другим ключом.

Ответ — документ:
`id`, `review_id`, `return_id`, `payable_id`, `request_id`, `amount`, `currency`,
`posting_date`, `document_no`, `reason`, `outstanding_before`, `outstanding_after`,
`confirmed_by_name`, `confirmed_at`. Денежные поля — строки с двумя знаками.
Дата подтверждения — ISO timestamp. Записи не изменяются/не удаляются через API.

Каждый отдельный POST с новым UUID — **новый денежный документ**. Номер основания
не служит ключом идемпотентности. Несколько корректировок одного возврата
допускаются, но каждая ограничена остатком выбранного долга. Полная сумма
возмещения не вычисляется; рассмотрение остаётся pending.

## Ошибки и финансовый эффект

Ошибки валидации/состояния: `{ "error": "...", "code": "..." }`.
401 — стандартный отказ авторизации; 403 `permission_denied`;
404 `not_found`; 400 `invalid_input`; 405 `method_not_allowed`.
409: `idempotency_conflict`, `invalid_return`, `invalid_payable`,
`currency_mismatch`, `insufficient_outstanding`, `period_closed`.
Неизвестная серверная ошибка возвращает общий 500 без внутренних деталей.

Уменьшается только текущий остаток долга. При нуле — `settled_by_adjustment`,
иначе сохраняется open/partially_paid. Оплата оставшейся части также даёт
settled_by_adjustment при нуле, если по долгу есть корректировки; чистая оплата
без корректировок сохраняет paid. Новые платёжные записи и банковские
движения не создаются; исходная сумма/сверка/заказ/приёмка неизменны.
Складская оценка не является пределом или суммой возмещения. Закрытое
рассмотрение, денежный возврат, FX и полный цикл претензии не реализованы.
Ответы с финансовыми данными имеют `Cache-Control: private, no-store`.
