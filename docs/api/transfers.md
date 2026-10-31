# Warehouse transfer workflow

This feature retains Django ORM, RBAC and database transactions. A new service
would introduce distributed stock transactions without a demonstrated benefit.
All writes lock warehouse rows in stable ID order and the transfer row.

## Lifecycle and stock accounting

`draft → pending_approval → approved → in_transit → received`.
Review can `return` to draft (reason required), or `reject` terminally (reason
required). Sender can cancel draft, pending or approved documents. Nothing can
cancel a dispatched document or change its lines. Receive is for the complete
quantity: partial receipt/shortage claims require a separate later process.

Drafts and approvals do not reserve or alter stock. Availability is checked on
create/edit and rechecked at dispatch; an approved document may therefore fail
dispatch if other documents consumed its stock. Dispatch decrements source
physical stock and batch, freezes source average cost in each line and creates
only `transfer_out` ledger entries. Destination stock remains unchanged while
in transit. Receive increments destination stock/batch and creates only
`transfer_in` entries, using the frozen cost and weighted destination average.
Transit quantity is derived from immutable dispatched document lines, separately
from both physical balances. Duplicate dispatch/receive by an authorized actor
returns success without duplicate stock, ledger or audit writes.

One SKU can appear once per document (existing unique constraint). A SKU spanning
multiple batches or source locations needs separate documents. Source and
receiver locations are optional but must belong to their respective warehouses.
A selected batch must match its source number, expiry and quantity. Unbatched
stock means physical stock minus all tracked batch quantities: omitting a batch
cannot consume tracked stock. Same destination batch number with another expiry
returns a conflict and leaves the entire transfer in transit.

## Permissions and privacy

All routes require bearer authentication. Module permissions are independent of
warehouse assignment. Non-directors manage only warehouses whose manager FK
points to them. Director has project-standard full permissions and scope.

- List/detail/catalog: `warehouse.transfer.read`; either endpoint assigned.
- Create/edit/submit/cancel: `warehouse.transfer.manage`, source assigned.
- Review: `warehouse.transfer.approve`, source assigned or director, actor must
  differ from creator. This is fixed independent approval, not a configurable
  generic approval-flow editor.
- Dispatch: existing `warehouse.transfer.post`, source assigned.
- Receive: `warehouse.transfer.receive`, destination assigned.
- Returned costs: separate `warehouse.cost.read`.

Counterparty document metadata (warehouse names, chosen locations, quantities,
shared comments/history) is visible to either participant. Counterparty stock,
manager identity and other documents are not exposed. Destination selector
exposes warehouse names/locations to support routing, never their inventory.
Internal audit snapshots contain before/after header and line data; public
history includes only actor, action, timestamp and action comment, not raw cost
snapshots. Changing or revoking module rights blocks direct writes as well as UI.

## API

- `GET /api/warehouse/transfers/catalog`: `{sources,destinations,skus,stock,permissions}`.
  Warehouse rows: `{id,name_ru,name_ky,name_zh,locations:[{id,code}]}`. Sources
  are assigned warehouses; destinations are routing metadata for all warehouses.
  Stock rows: `{warehouse_id,sku_id,location_id,location_code,qty,unbatched_qty,
  batches:[{batch_no,expiry_date,qty}],avg_cost?}`; assigned warehouses only.
- `GET /api/warehouse/transfers?warehouse_id=&status=&id=&offset=0&limit=50`:
  `{items,count}`, max limit 100. Warehouse filter must itself be in scope.
- `POST /api/warehouse/transfers`: `{transfer_no,source_warehouse_id,
  destination_warehouse_id,comment?,items:[{sku_id,qty,source_location_id?,
  destination_location_id?,batch_no?,expiry_date?}]}`. Qty positive integer,
  1–100 unique active SKU lines. Returns 201 `{id,status}`.
- `PATCH /api/warehouse/transfers/{id}`: same payload, draft source only.
  Route and document number are immutable; edit comment/lines only. Different
  route requires cancellation and a new document. Full lines replace old lines
  atomically, with before/after audit snapshots retained.
- `POST /api/warehouse/transfers/{id}/submit`: no body required.
- `POST /api/warehouse/transfers/{id}/review`: `{decision:approve|return|reject,
  comment?}`; nonblank comment required for return/reject.
- `POST /api/warehouse/transfers/{id}/dispatch`: no body required.
- `POST /api/warehouse/transfers/{id}/receive`: no body required.
- `POST /api/warehouse/transfers/{id}/cancel`: `{comment?}`.
- Legacy `POST /api/warehouse/transfers/{id}/post`: 410
  `legacy_endpoint_retired`; never bypasses approval or receiving.

Action responses are `{id,status}`. GET DTO contains `id,transfer_no,status`,
source/destination IDs and multilingual names, `comment,review_comment`,
`created_at,approved_at,dispatched_at,received_at` and corresponding
`*_by_name`, `allowed_actions`, `history`, `in_transit_qty` and `items`.
History row: `{id,action,actor_name,created_at,comment}`. Item: `{id,sku_id,
sku_code,name_ru,name_ky,name_zh,qty,source_location_id,source_location_code,
destination_location_id,destination_location_code,batch_no,expiry_date,
in_transit_qty,unit_cost?}`. Transit quantities and costs are decimal strings;
item qty is integer. Cost omitted before dispatch or without cost permission.
`allowed_actions` are `edit,submit,review,dispatch,receive,cancel` as appropriate.

Errors follow WMS `{error,code}`: `validation_error` 400,
`permission_denied` 403 (including invalid action state), `not_found` 404,
`conflict`, `insufficient_stock`, `batch_required`, `batch_conflict` 409,
`legacy_endpoint_retired` 410. Frontend localizes codes.

## Migration and compatibility

`0046_stock_transfer_workflow` adds lifecycle metadata, line locations/batch/
frozen cost and the two new permission records. It does not automatically grant
new approval/receive rights to existing non-director roles. Configure these via
RBAC. Existing received transfers remain historical; no ledger is rewritten.
Existing draft transfers require submit/independent review before dispatch.
Migration has not been applied to the working database by this task.
