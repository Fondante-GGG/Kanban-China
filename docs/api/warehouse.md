# Online WMS API

This stage extends the existing Django ORM/API stack. A new service or language
would add cross-service transactions and deployment risk without improving the
current small document workflows; the existing Django transactions and RBAC are
retained. No schema change or production database migration is required.

## Authorization and scope

All endpoints require the existing bearer authentication. A director sees all
warehouses; every other role sees only warehouses whose `manager_id` equals the
current user. Module permissions remain independently required. No automatic
company-wide access follows from having a `warehouse.*` permission. The current
single manager FK is a limitation: multiple staff assignments need a later data
model extension. All GET lists, explicit warehouse filters and mutations enforce
this scope. An inaccessible explicit warehouse filter returns 403; inaccessible
documents return 404.

- Inventory, movements and expiry alerts: `warehouse.inventory.read`.
- Receipts: GET `warehouse.receipt.read`; POST `warehouse.receipt.manage`;
  separate posting `warehouse.receipt.post`.
- Counts: GET `warehouse.count.read`; POST `warehouse.count.manage`;
  approval `warehouse.count.approve`.
- Photo-backed writeoffs: `warehouse.writeoff.read/manage/approve/post`, with
  independent approval and a separate stock-posting action; see `writeoffs.md`.
- Transfers now follow the separately approved workflow in `transfers.md`:
  read access to either side; source-side management/dispatch, independent
  approval and destination-side receipt. Legacy direct posting is retired.
- `warehouse.cost.read` independently controls every returned cost field and
  receipt cost overrides; director follows the project's existing permission
  expansion.

The API never returns procurement unit prices, average costs or movement costs
without the separate cost permission. Read-only users may see their scoped
receipts/orders' number, quantity and product names without financial values.

## Catalog

`GET /api/warehouse/catalog` requires at least one warehouse permission.

```text
{
  permissions: ["warehouse.inventory.read", ...],
  warehouses: [{id, name_ru, name_ky, name_zh, locations: [{id, code}]}],
  skus: [{id, sku_code, name_ru, name_ky, name_zh}],
  purchase_orders: [{id, po_no, currency, items: [
    {id, sku_id, sku_code, name_ru, name_ky, name_zh,
     ordered_qty, received_qty, unit_cost?}
  ]}]
}
```

SKUs are the active global product master without prices, available only when at
least one warehouse is in scope. This does not grant procurement write access.
Orders are supplied only to receipt managers. They must be approved or partially
received and have remaining quantities. Non-directors additionally see only
orders in their own department (no department means no candidate orders).
Purchase orders currently have no warehouse FK: one may receive an authorized
order into any assigned warehouse. There is no implied supplier-portal access.

## Paginated lists

`GET /api/warehouse/inventory`, `/movements`, `/receipts`, `/counts`, `/transfers`
accept `warehouse_id?`, `limit` (1–100, default 50), `offset` (0–1000000,
 default 0), and return `{items: [...], count: total}`. Ordering is stable.
Receipts additionally accept `purchase_order_id?`; receipts, counts and transfers
accept exact `id?` for scoped document lookup from a ledger source link.
Unknown source documents are not made visible through the movement list.

Common warehouse fields are `warehouse_id`, `warehouse_name_ru/ky/zh`;
common product fields are `sku_id`, `sku_code`, `name_ru/ky/zh`.

- Inventory: `id`, warehouse/product fields, `location_id`, `location_code`,
  `qty`, optional `avg_cost`, `batches:[{batch_no, expiry_date, qty}]`.
- Movements: `id`, warehouse/product/location fields, `qty_delta`,
  `movement_type`, `source_type`, `source_id`, nullable `source_no`, `reason`,
  `posted_at`, optional `unit_cost`. Source numbers are fetched in bulk. A
  transfer number is available to an assigned participant; access to its
  document still requires `warehouse.transfer.read`. Other warehouse balances
  remain outside the ledger's scope.
- Receipts: `id`, `receipt_no`, `purchase_order_id`, `po_no`, warehouse fields,
  `status`, `comment`, `received_at`, `allowed_actions:["post"]` when authorized;
  `items:[{id, po_item_id, product fields, qty, location_id, location_code,
  batch_no, expiry_date, discrepancy_reason, unit_cost?}]`.
- Counts: `id`, `count_no`, warehouse fields, `status`, `created_at`,
  `allowed_actions:["approve"]` when authorized;
  `items:[{product fields, system_qty, actual_qty, reason}]`.
- Transfers: full actor-specific DTO, immutable route, locations, batches,
  transit quantities and history are documented in `transfers.md`.
- Writeoffs: full reason, line, photo-evidence, history and actor-action DTOs are
  documented in `writeoffs.md`. Ledger entries use `stock_writeoff` sources,
  `issue` movements and exact-ID links to their primary documents.

The frontend must use server actions and also handle permission revocation or
stale state (403/409) after any list response.

## Receipt creation and posting

`POST /api/warehouse/receipts`:

```json
{
  "receipt_no": "REC-001",
  "purchase_order_id": 1,
  "warehouse_id": 1,
  "comment": "",
  "items": [{"po_item_id": 1, "qty": 3, "location_id": null,
             "batch_no": "", "expiry_date": null,
             "discrepancy_reason": "Partial delivery"}]
}
```

Rows are unique by PO item, quantity is a positive integer and may not exceed
the current order remainder. Partial receipt requires a reason. Optional
`unit_cost` is derived from the order if omitted; specifying it requires cost
permission. A supplied cost must be finite, non-negative and have at most two
decimal places. Location must belong to the receipt warehouse. Batch and ISO
expiry date must be supplied together. Creation returns 201 `{id,receipt_no,status}`.

`POST /api/warehouse/receipts/{id}/post` has no body and returns
`{id,status,purchase_order_status}`. Only draft documents on approved/partially
received orders may post; legacy drafts are revalidated at posting too.
All lines, purchase-order quantities, weighted costs, batch quantities, ledger
entries, document statuses and audit commit together. Any failure rolls back the
entire document. Repeated posting returns 409 and never duplicates stock.

## Counts

`POST /api/warehouse/counts` accepts
`{count_no,warehouse_id,items:[{sku_id,actual_qty,reason}]}` and returns 201
`{id,count_no,status:"counted"}`. Actual quantities are finite, non-negative,
up to three decimal places. All row SKUs are unique and active. A difference
requires a reason. The server snapshots system quantity, never trusts a
client-supplied snapshot, and does not alter stock until approval.

`POST /api/warehouse/counts/{id}/approve` has no body and returns `{id,status}`.
Approval rejects any changed current quantity with 409; the user must create a
fresh count. All lines roll back together on failure. This stage counts only
**stock without a location** (`location_id IS NULL`), not the entire warehouse.
Differences on tracked batch stock are rejected with 409 (`batch_adjustment_required`) pending batch-aware
adjustment support. Approval is recorded in audit; repeat returns 409.

## Transfers and expiry

Transfers have a dedicated WMS tab and now use independent approval, sender
dispatch and destination receipt, including batch and location handling.
`POST /warehouse/transfers/{id}/post` returns 410; it cannot bypass the workflow.
See `transfers.md` for migration, new permissions and the full contract.

`GET /api/warehouse/alerts/expiry?days=30&warehouse_id=...` requires inventory
read and returns `{as_of,days,batches,certificates}`. Days must be 1–365. Batch
rows include warehouse/product/location fields, `id`, `batch_no`, `expiry_date`,
`qty`, `expired`. Certificates include `id`, product fields, `number`,
`expires_at`, `expired`; non-directors see only SKUs present in scoped stock.
Certificate file paths are never returned here. Lists are capped at 500 rows with `batches_count`, `certificates_count`, and
`truncated` metadata;
notification delivery is not implemented by this read-only endpoint.

## Transactions and rollout

All API stock writers first lock warehouse rows in stable ID order. This also
serializes creation of missing stock rows with nullable locations, which the
legacy SQL unique constraint alone does not protect. Documents and PO rows are
locked before transitions; counts detect stale snapshots. Decimal bounds are
checked before saving resultant stock/batch quantities. Creation and posting
write an operation audit in the same transaction.

Cost-free drafts can now omit unit_cost. Existing drafts created on unapproved
orders, without partial-delivery reasons or with invalid quantities cannot post;
they require correction through an appropriate future editing/cancellation
workflow. No direct inventory write endpoint exists. This stage adds no
write-offs/photos, returns, PDA/offline synchronization, batch transfers or
batch-aware counts.

## Errors

Failures return `{error: humanReadableMessage, code: stableCode}`. Codes:
`validation_error` (400), `permission_denied` (403), `not_found` (404),
`conflict` (409), `batch_adjustment_required` / `batch_transfer_required` (409),
`method_not_allowed` (405). Authentication follows the common
middleware's 401 behavior. Frontend localizes stable codes, not English messages.
Unexpected persistence/audit failures are handled by shared middleware; database
writes roll back first.


## Возврат поставщику

Отдельный receipt-bound контракт, права, фото и финансовая очередь описаны в
[Supplier returns](supplier-returns.md).
