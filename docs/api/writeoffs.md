# Stock writeoffs with private photo evidence

This feature retains the current Django ORM, private filesystem storage and
Pillow image decoder. A new service would add distributed stock/file operations
without a demonstrated scale benefit. Database writes use transactions and the
same warehouse-row locks as receipts, counts and transfers.

## Lifecycle and authorization

`draft → pending_approval → approved → posted`.

Independent review may return to draft or reject terminally; return and reject
require a comment. The creator cannot approve their own document. Cancellation
is possible in draft, pending or approved states, never after posting.
Only posting changes physical stock, batches and the immutable stock ledger.
Approval does not reserve stock: availability is checked again when posting.

Every endpoint requires bearer authentication. Director has the existing full
scope/permissions; others can access only warehouses whose manager FK equals
their user ID. Current one-manager-per-warehouse limitation remains. Permission
alone does not grant company-wide warehouse access.

- `warehouse.writeoff.read`: catalog, document lists/details and photo download.
- `warehouse.writeoff.manage`: create/edit, upload/remove photos, submit/cancel.
- `warehouse.writeoff.approve`: independent review within authorized scope.
- `warehouse.writeoff.post`: post approved document; safe authorized retries.
- `warehouse.cost.read`: independently exposes posted per-line cost.

New permissions are seeded by `0047_stock_writeoffs` but not silently assigned
to existing employee roles. Working database migrations are not applied by this
implementation. Assign rights through RBAC after rollout. No generic approval
route editor, finance loss-account integration or notification scheduler is added.

## Catalog and document API

- `GET /api/warehouse/writeoffs/catalog`:
  `{warehouses:[{id,name_ru,name_ky,name_zh,locations:[{id,code}]}],
  skus:[{id,sku_code,name_ru,name_ky,name_zh}],
  stock:[{warehouse_id,sku_id,location_id,location_code,qty,unbatched_qty,
  batches:[{batch_no,expiry_date,qty}]}],permissions}`.
  Stock and SKU selectors are based on positive stock in assigned warehouses.
  No prices or private storage paths are returned.
- `GET /api/warehouse/writeoffs?warehouse_id=&id=&status=&limit=50&offset=0`:
  `{items,count}`. Limit 1–100, offset 0–1,000,000. Explicit foreign warehouse
  filter returns 403; inaccessible document IDs are absent from scoped lists.
- `POST /api/warehouse/writeoffs` creates draft. JSON:

```json
{
  "writeoff_no": "WO-2026-001",
  "warehouse_id": 1,
  "reason": "Expired goods",
  "items": [{"sku_id": 1, "qty": "1.250", "location_id": 2,
             "batch_no": "B-1", "expiry_date": "2026-10-01"}]
}
```

- `PATCH /api/warehouse/writeoffs/{id}` accepts the same complete draft payload.
  Number and warehouse are immutable; only reason/items are replaced, in draft.
- Creation returns 201 `{id,status}`; edits/actions return 200 `{id,status}`.
- `POST /{id}/submit`: requires nonempty reason, items and at least one active
  photo. Every active photo's stored file must exist, including on posting.
- `POST /{id}/review`: `{decision:"approve"|"return"|"reject",comment:"..."}`.
- `POST /{id}/post`: approved only; authorized retries return posted without
  another stock movement or audit event.
- `POST /{id}/cancel`: optional `{comment:"..."}`; only before posting.

Document DTO fields: `id`, `writeoff_no`, `warehouse_id`,
`warehouse_name_ru/ky/zh`, `status`, `reason`, `review_comment`,
`created_at`, `created_by_name`, `approved_at/by_name`, `posted_at/by_name`,
`allowed_actions`, `items`, `photos`, `history`.

Item DTO: `id`, `sku_id`, `sku_code`, `name_ru/ky/zh`, `location_id/code`,
`qty` (decimal string), `batch_no`, `expiry_date`, optional `unit_cost`.
Actions: `edit`, `upload_photo`, `delete_photo`, `submit`, `review`, `post`,
`cancel`; use server actions and handle later 403/409 changes.
History is `{id,action,actor_name,created_at,comment}` without private paths or
raw audit cost snapshots. Events use `warehouse.writeoff_created`, `_edited`,
`_photo_uploaded`, `_photo_removed`, `_submit`, `_review_approve`,
`_review_return`, `_review_reject`, `_post`, `_cancel`.

## Quantity, batch and atomic stock rules

One document accepts 1–100 lines, finite positive quantities up to three decimal
places within stock decimal bounds. Tuple `(sku,location,batch_no)` must be
unique even when location is null; the server validates this independently of
SQL NULL uniqueness. Different batches/locations of a SKU may share a document.
The warehouse lock protects cumulative quantities across all its lines.

Batch number and expiry are supplied together and must match source inventory.
Unbatched availability equals physical quantity minus all tracked batch
quantities; omitting a batch cannot consume tracked stock. Posting freezes the
current average cost, decrements the exact stock/batch and emits negative
`issue` movements with `source_type="stock_writeoff"`, source document ID and
reason. Source numbers appear in the movement API for document lookup.

Draft edits, photo metadata and all transitions record full before/after audit
snapshots in the same transaction. A failed line or failed audit rolls back
stock, cost snapshots, ledger and document status together. PostgreSQL warehouse
row locks serialize writers; the real contention test is skipped on SQLite.

## Photos and private storage

- `POST /api/warehouse/writeoffs/{id}/photos`: multipart field `file`, exactly
  one photo per request. Maximum five active photos, ten MiB per file and twenty
  million decoded pixels. JPEG, PNG and WebP only; actual bytes are decoded and
  verified with Pillow, animations and unsupported formats are rejected.
- Authorization and editable-state checks happen before decoding or writing.
  The image is re-encoded with canonical pixels; orientation is applied and
  original EXIF/comments are stripped. Extension/MIME follow decoded format,
  not the submitted extension. Filename is a sanitized display label.
- Files use UUID names under `PRIVATE_MEDIA_ROOT/writeoffs/`, outside public
  MEDIA_URL. A failed metadata/audit transaction removes only its newly created
  file. Existing evidence is not deleted by failure cleanup.
- Success 201 and photo DTO: `{id,file_name,content_type,size,download_url}`.
  `size` describes canonical stored bytes. `download_url` is an authenticated
  API route, never a public path or URL containing a token.
- `GET /api/warehouse/writeoffs/{id}/photos/{photo_id}/download` rechecks current
  read permission and warehouse assignment on every request. Returns attachment
  bytes, actual content type, `X-Content-Type-Options: nosniff` and
  `Cache-Control: private, no-store`. Frontend may preview an authenticated Blob
  and must revoke its object URL.
- `DELETE /api/warehouse/writeoffs/{id}/photos/{photo_id}`: draft only. Marks
  photo inactive and audits removal; original private bytes are retained for
  evidence history. Removed photos are absent from DTOs and not downloadable.
  Retention/backup capacity policy is an operational follow-up, not automated
  deletion. Rejection/cancellation retains current evidence.

Photo upload/removal is frozen outside draft. A returned draft can be edited and
resubmitted; its previous photo/version changes remain in internal audit.

## Errors

Errors use `{error,code}`. Stable codes: `validation_error` (400),
`permission_denied` (403), `not_found` (404), `conflict` (409),
`photo_required` (409), `invalid_photo` (400), `photo_limit` (409),
`insufficient_stock` (409), `batch_required` (409), `method_not_allowed` (405).
Authentication follows shared middleware 401 behavior. Unexpected persistence
or storage failures use shared server-error handling after rollback.

## Private media deployment

Private files are excluded from Git and Docker build contexts. Compose declares
the persistent `backend_private_media` volume at `/app/backend/private_media`,
matching `PRIVATE_MEDIA_ROOT`; it is not served by the public media URL.
Configuration was validated with `docker compose config --quiet`; no containers
were started or recreated during implementation.

For an existing deployment that already has private files in a container's
writable layer, preserve those files and migrate them into the new volume
before recreating that container. Adding the volume does not copy data out of
an old container. Backups must cover both the database and private media.
