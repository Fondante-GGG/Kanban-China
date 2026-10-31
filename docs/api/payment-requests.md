# Заявки на оплату — API v1

Статус: контракт согласован TL/BE, реализация проходит проверки. Модульный монолит.
ТЗ Г.6. Последовательный маршрут `finance_payment_request` настраивается через
существующий `/api/approval-flows`; без активного маршрута submit возвращает409.
Порогов сумм, параллельного согласования или fallback-директора здесь нет.

## Права

GET списка/каталога/деталей: `finance.payable.read` либо `finance.payment.manage`.
Создание, proof upload/delete и платёж: payment.manage. Редактирование и submit/cancel дополнительно требуют автора заявки; другой финансист не переписывает согласуемые поля.
Решение: approval.read + approval.act, только текущий назначенный сотрудник,
никогда автор заявки (включая директора). Approver видит финансовый snapshot
в своём обычном approval detail; это не даёт доступа ко всему финансовому реестру.

## Endpoints (prefix /api)

- GET `/finance/payment-requests?limit=20&offset=0&q=&status=&id=` →
  `{items: PaymentRequest[],count,limit,offset,can_create}`. maxlimit100, exactid optional.
- POST `/finance/payment-requests` →201, точный повтор UUID200.
- GET `/finance/payment-requests/catalog?limit=20&offset=0&q=&payable_id=&account_id=` →
  `{payables:[{id,supplier_id,supplier_name,source_id,amount,outstanding_amount,currency,status}],payable_count,accounts:[{id,name,currency}],limit,offset,flow_configured}`.
  IDs — integer; amounts — decimal strings. Остатки банков не выдаются каталогом.
  Exact id сохраняет выбранное основание при редактировании за пределами страницы.
- GET/PATCH `/finance/payment-requests/{id}` →PaymentRequest.
- POST `/finance/payment-requests/{id}/submit` `{}` →202 PaymentRequest.
- POST `/finance/payment-requests/{id}/cancel` `{comment:string}` →200 PaymentRequest.
- POST `/finance/payment-requests/{id}/proofs` multipart `file` →201 Proof.
- DELETE `/finance/payment-requests/{id}/proofs/{proof_id}` →200 `{id}`; logical deletion.
- GET `/finance/payment-requests/{id}/proofs/{proof_id}/download` →protected bytes.
- POST `/approvals/{approval_id}/actions` existing `{action:'approve'|'reject'|'return',comment}` →
  `{id,status,assigned_to_id,current_node}`. Reject/return require reason.
- POST `/finance/payables/{payable_id}/payments` now requires
  `{payment_request_id,account_id,amount,payment_date,transaction_no,proof_id}` →
  201 first /200 exact replay `{id,payment_request_id,payable:{id,supplier_id,purchase_order_id,amount,outstanding_amount,currency,status}}`.
  Missing approved request409 approval_required. One request funds exactly one payment.

Create body: `{request_id:UUID,request_no:string<=64,payable_id:integer,account_id:integer,
amount:positive decimal-string<=14integer+2fraction digits,currency:uppercase3,
planned_payment_date:YYYY-MM-DD,purpose:nonempty string<=4000}`.
PATCH replaces financial fields (same body except immutable request_id/request_no).
Draft and returned only; any new submission creates a new immutable approval snapshot.

PaymentRequest: `{id,request_id,request_no,payable_id,supplier_id,supplier_name,
payable_outstanding_amount,account_id,account_name,amount,currency,planned_payment_date,
purpose,status,created_by_id,created_by_name,created_at,approval_id,approval_status,
assigned_to_id,assigned_to_name,current_node,payment_id,allowed_actions,proofs,history,history_count}`.
States: draft,pending_approval,approved,returned,rejected,cancelled,paid.
Allowed actions: edit,submit,cancel,pay,upload_proof,delete_proof.
Proof: `{id,file_name,content_type,size,download_url}`.
History: `[{action,actor_id,actor_name,comment,created_at}]`. Detail returns100most recent events, newestfirst, with history_count. List is a summary with empty history/proofs and an aggregated real history_count.
Approval snapshot: immutable financial fields above + `route:[{order,assignee_id,assignee_name}]`.
No bank balance, employee versions or raw storage paths are exposed.

Proof is actual private stored evidence, not browser filename/text path. PDF<=15MiB
with header/end marker validation; JPEG/PNG/WebP<=10MiB/20MP decode/re-encode with
metadata removed. Up to5active files; upload/removal draft,returned,approved only,
paid evidence immutable. An active existing proof belonging to this request is
required at execution. PDF validation is not malware scanning certification.

All request mutations guard the planned month; edit locks old/new months in order.
Final payment rechecks active account, exact approved amount/account/date/currency,
current debt and bank balance, proof and open period. Approval reserves no funds.
Partial debt is paid via several exact requests. Old payments remain readable with
nullable request links; no invented approvals are backfilled.

Errors:400 invalid_input;403 permission_denied;404 not_found;409 period_closed,
approval_required,request_conflict,invalid_state,flow_unconfigured,approver_unavailable,
insufficient_outstanding,insufficient_balance,currency_mismatch,idempotency_conflict,
transaction_conflict,proof_required. Same UUID with changedcreate payload conflicts.
Exact payment replay returns prior result even after the period closes, without
mutating money. Other payload with same request conflicts.
