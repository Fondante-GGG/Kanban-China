# Возвраты поставщику — проект API v1

Статус: складской контракт реализован и прошёл независимое ревью.
Область и финансовые ограничения: ADR-0004.

Все маршруты под `/api`, с действующей авторизацией. Складские ответы доступны
только назначенному складу; директору — все. Права
`warehouse.return.read/manage/approve/post`, стоимость — `warehouse.cost.read`.
Финансовый реестр требует `finance.payable.read` и не даёт доступ к редактированию
склада. Данные поставщика ограничены id/названием, без контактов и банковских данных.

| Метод/путь | Контракт |
| --- | --- |
| GET /warehouse/returns/catalog | limit (default50,max100), offset, q (receipt_no,<=64), receipt_id, warehouse_id; receipt_count/limit/offset, warehouses, receipts (posted only, receipt_no, warehouse_id, supplier_id/name, items: receipt_item_id, sku_id/code/name_ru/ky/zh, location_id/code, batch_no, expiry_date, received_qty, returned_qty, returnable_qty), permissions |
| GET /warehouse/returns | items, count; фильтры id/warehouse_id/status; limit 1..100 default50, offset 0..1000000 |
| POST /warehouse/returns | `{return_no, receipt_id, reason_type: damage\|expiry\|other, reason, items:[{receipt_item_id,qty}]}` → 201 `{id,status}` |
| PATCH /warehouse/returns/{id} | то же полное тело; return_no и receipt_id неизменны; только draft |
| POST /warehouse/returns/{id}/submit | перевод pending_approval |
| POST /warehouse/returns/{id}/review | `{decision:approve\|return\|reject,comment}`; комментарий обязателен для return/reject |
| POST /warehouse/returns/{id}/post | approved → posted; повтор авторизованного post → 200 без повторных эффектов |
| POST /warehouse/returns/{id}/cancel | `{comment}`; только до posted/rejected/cancelled |
| POST /warehouse/returns/{id}/photos | multipart file; JPEG/PNG/WebP, до5 фото,10MiB/20MP, канонические пиксели без metadata |
| DELETE /warehouse/returns/{id}/photos/{photo_id} | только draft; softremove с аудитом |
| GET /warehouse/returns/{id}/photos/{photo_id}/download | повторная проверка прав/склада, private no-store |
| GET /finance/supplier-returns | pending-записи со ссылкой на return, receipt, supplier, posted_at, source_currency (только валюта исходного заказа), valuation_currency:null, valuation_status:currency_unresolved, stock_valuation, items и photos; это не debt/credit amount; pagination как выше, return_id exact filter |

| GET /finance/supplier-returns/{review_id}/photos/{photo_id}/download | finance.payable.read; проверка связи review/return/photo и актуальных прав, private no-store |

Строки не повторяются; qty — положительное целое. Сервер выводит склад, поставщика,
SKU/ячейку/партию из приёмки. Каталог returnable_qty отражает лимит по истории,
а не резервирует текущий остаток. Утверждение также не резервирует остатки.

Документ ответа: id, return_no, receipt_id/receipt_no, warehouse_id/name_ru/ky/zh,
supplier_id/name, reason_type/reason, status, created_at/created_by_name,
approved_at/approved_by_name, posted_at/posted_by_name, review_comment,
allowed_actions, photos_required (по серверной дате), finance_review_status, items, photos, history. Строка:
id, receipt_item_id, sku_id/code/name_ru/ky/zh, location_id/code, qty (строка),
batch_no, expiry_date; unit_cost только с warehouse.cost.read и после post.
История: action,actor_name,created_at,comment без сырых аудитных снимков.
Фото: id,file_name,content_type,size,download_url.

Ошибки `{error,code}`: 400 validation_error, 403 permission_denied,
404 not_found (чужие документы скрыты), 409 insufficient_stock/receipt_limit/
photo_required/conflict, 405 method_not_allowed. Лимиты и фото повторно проверяются
при проведении; транзакция сохраняет остатки при любом отказе. Внешние события
не вводятся; локальные уведомления с entity_type=supplier_return.


Фотографии обязательны при damage/expiry и при любой истёкшей исходной партии
(expiry_date < серверной даты), даже с reason_type=other. Если товар истёк после
утверждения документа без фото, проведение блокируется: отменить документ и создать
новый с доказательствами. Финансовое фото доступно по отдельному защищённому URL,
который не предоставляет права чтения чужого склада. До проведения review отсутствует.
Складская оценка имеет неразрешённую валюту; она не форматируется как KGS/CNY и
не равна долгу/возмещению. Перечисленные выше складские endpoints и очередь не проводят денежную корректировку.
Отдельное подтверждение уменьшения долга описано в
[контракте корректирующих документов](supplier-return-corrections.md).

Миграция 0048_supplier_returns создаёт только новые таблицы/права. Рабочая БД не
мигрируется автоматически; обратная миграция после документов потребует сохранения
истории и отдельного решения, удаление данных не является безопасным rollback.
