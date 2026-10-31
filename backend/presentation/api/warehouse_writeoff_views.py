"""Approved stock writeoffs with private, canonical photo evidence."""
from collections import defaultdict
from datetime import date
from decimal import Decimal
from io import BytesIO
from pathlib import Path
from uuid import uuid4
import warnings

from django.core.files.base import ContentFile
from django.core.exceptions import SuspiciousFileOperation
from django.http import FileResponse, JsonResponse
from django.http.multipartparser import MultiPartParserError
from django.db import transaction
from django.utils import timezone
from django.utils.text import get_valid_filename
from PIL import Image, ImageOps, UnidentifiedImageError

from backend.infrastructure.persistence.models import (
    GoodsSKUModel, OperationLogModel, StockBatchModel, StockInventoryModel,
    StockMovementModel, StockWriteoffModel, StockWriteoffItemModel,
    StockWriteoffPhotoModel, WarehouseLocationModel,
)
from backend.infrastructure.persistence.storage import PrivateMediaStorage
from backend.presentation.api.utils import parse_json_body
from backend.presentation.api.warehouse_views import (
    WmsError, decimal, endpoint, integer, lock_warehouses, method, rows,
    scope, sku_data, text, warehouse, wh_data,
)

MAX_PHOTOS = 5
MAX_PHOTO_BYTES = 10 * 1024 * 1024
MAX_PHOTO_PIXELS = 20_000_000
FORMATS = {'JPEG': ('image/jpeg', '.jpg'), 'PNG': ('image/png', '.png'), 'WEBP': ('image/webp', '.webp')}


def visible(request):
    return StockWriteoffModel.objects.filter(warehouse__in=scope(request))


def actions(request, doc):
    result = []
    if 'warehouse.writeoff.manage' in request.wms_permissions:
        if doc.status == 'draft':
            result.extend(['edit', 'upload_photo', 'delete_photo', 'submit'])
        if doc.status in ('draft', 'pending_approval', 'approved'):
            result.append('cancel')
    if ('warehouse.writeoff.approve' in request.wms_permissions and doc.status == 'pending_approval'
            and doc.created_by_id != request.user_entity.id):
        result.append('review')
    if 'warehouse.writeoff.post' in request.wms_permissions and doc.status == 'approved':
        result.append('post')
    return result


def require_action(request, doc, action):
    if action not in actions(request, doc):
        raise WmsError('Action not permitted for this document or actor', 'permission_denied', 403)


def locked(request, doc_id):
    found = visible(request).filter(id=doc_id).first()
    if found is None:
        raise WmsError('Writeoff not available', 'not_found', 404)
    lock_warehouses(found.warehouse_id)
    return StockWriteoffModel.objects.select_for_update().select_related('warehouse').get(id=found.id)


def snapshot(doc):
    return {'writeoff_no': doc.writeoff_no, 'warehouse_id': doc.warehouse_id,
            'reason': doc.reason, 'status': doc.status, 'review_comment': doc.review_comment,
            'items': [{'sku_id': row.sku_id, 'location_id': row.location_id, 'qty': str(row.qty),
                       'batch_no': row.batch_no, 'expiry_date': row.expiry_date.isoformat() if row.expiry_date else None,
                       'unit_cost': str(row.unit_cost) if row.unit_cost is not None else None}
                      for row in doc.items.order_by('id')],
            'photos': [{'id': photo.id, 'file_name': photo.file_name, 'content_type': photo.content_type,
                        'size': photo.size, 'is_active': photo.is_active} for photo in doc.photos.order_by('id')]}


def audit(request, doc, action, before, comment=''):
    OperationLogModel.objects.create(actor_id=request.user_entity.id, action='warehouse.writeoff_' + action,
        business_type='stock_writeoff', business_id=doc.id, old_data=before,
        new_data={**snapshot(doc), 'event_comment': comment}, ip_address=request.META.get('REMOTE_ADDR', ''))


def evidence(doc):
    photos = list(doc.photos.filter(is_active=True))
    storage = PrivateMediaStorage()
    if not photos or any(not storage.exists(photo.file_path) for photo in photos):
        raise WmsError('Photo evidence is required and every attached file must be available', 'photo_required', 409)


def validate_stock(wh, prepared):
    """Validate cumulative lines, including unbatched stock, under warehouse lock."""
    grouped = defaultdict(list)
    for row in prepared:
        grouped[(row['sku'].id, row['location'].id if row['location'] else None)].append(row)
    for (sku_id, loc_id), lines in grouped.items():
        stock = StockInventoryModel.objects.select_for_update().filter(warehouse=wh, sku_id=sku_id, location_id=loc_id).first()
        total = sum((row['qty'] for row in lines), Decimal(0))
        if stock is None or total > stock.qty:
            raise WmsError('Source inventory is insufficient', 'insufficient_stock', 409)
        batches = {batch.batch_no: batch for batch in stock.batches.select_for_update().all()}
        unbatched = stock.qty - sum((batch.qty for batch in batches.values()), Decimal(0))
        for row in lines:
            if row['batch_no']:
                batch = batches.get(row['batch_no'])
                if batch is None or batch.expiry_date != row['expiry_date'] or batch.qty < row['qty']:
                    raise WmsError('Batch unavailable or quantity insufficient', 'insufficient_stock', 409)
            elif row['qty'] > unbatched:
                raise WmsError('Select a batch for tracked stock', 'batch_required', 409)


def write_draft(request, body, doc=None):
    wh = warehouse(request, body.get('warehouse_id'))
    number = text(body.get('writeoff_no'), 64, True)
    reason = text(body.get('reason'), 4000, True)
    if doc is not None and (doc.warehouse_id != wh.id or doc.writeoff_no != number):
        raise WmsError('Writeoff number and warehouse are immutable')
    if doc is None:
        lock_warehouses(wh.id)
    before = snapshot(doc) if doc else {}
    prepared, seen = [], set()
    for row in rows(body):
        sku = GoodsSKUModel.objects.filter(id=integer(row.get('sku_id'))).first()
        if sku is None:
            raise WmsError('SKU not found')
        location_id = row.get('location_id')
        location = WarehouseLocationModel.objects.filter(id=integer(location_id), warehouse=wh).first() if location_id is not None else None
        if location_id is not None and location is None:
            raise WmsError('Location belongs to another warehouse')
        qty = decimal(row.get('qty'))
        if qty == 0:
            raise WmsError('Quantity must be positive')
        batch_no = text(row.get('batch_no', ''), 128)
        expiry = row.get('expiry_date')
        if bool(batch_no) != bool(expiry):
            raise WmsError('Batch and expiry are required together')
        expiry = date.fromisoformat(expiry) if expiry else None
        key = (sku.id, location.id if location else None, batch_no)
        if key in seen:
            raise WmsError('Duplicate SKU, location and batch line')
        seen.add(key)
        prepared.append(dict(sku=sku, location=location, qty=qty, batch_no=batch_no, expiry_date=expiry))
    validate_stock(wh, prepared)
    creating = doc is None
    if creating:
        doc = StockWriteoffModel.objects.create(writeoff_no=number, warehouse=wh, reason=reason, created_by_id=request.user_entity.id)
    else:
        doc.reason = reason
        doc.save(update_fields=['reason'])
        doc.items.all().delete()
    StockWriteoffItemModel.objects.bulk_create([StockWriteoffItemModel(writeoff=doc, **row) for row in prepared])
    audit(request, doc, 'created' if creating else 'edited', before)
    return doc


def data(request, doc, logs=()):
    result = {'id': doc.id, 'writeoff_no': doc.writeoff_no, **wh_data(doc.warehouse), 'status': doc.status,
              'reason': doc.reason, 'review_comment': doc.review_comment, 'created_at': doc.created_at.isoformat(),
              'created_by_name': doc.created_by.full_name, 'allowed_actions': actions(request, doc),
              'items': [], 'photos': [], 'history': []}
    for stage in ('approved', 'posted'):
        actor, stamp = getattr(doc, stage + '_by'), getattr(doc, stage + '_at')
        result[stage + '_by_name'] = actor.full_name if actor else None
        result[stage + '_at'] = stamp.isoformat() if stamp else None
    for item in doc.items.all():
        row = {'id': item.id, **sku_data(item.sku), 'location_id': item.location_id,
               'location_code': item.location.code if item.location else None, 'qty': str(item.qty),
               'batch_no': item.batch_no, 'expiry_date': item.expiry_date.isoformat() if item.expiry_date else None}
        if 'warehouse.cost.read' in request.wms_permissions and item.unit_cost is not None:
            row['unit_cost'] = str(item.unit_cost)
        result['items'].append(row)
    result['photos'] = [{'id': photo.id, 'file_name': photo.file_name, 'content_type': photo.content_type, 'size': photo.size,
                         'download_url': f'/api/warehouse/writeoffs/{doc.id}/photos/{photo.id}/download'}
                        for photo in doc.photos.all() if photo.is_active]
    result['history'] = [{'id': log.id, 'action': log.action, 'actor_name': log.actor.full_name if log.actor else '',
                          'created_at': log.created_at.isoformat(), 'comment': log.new_data.get('event_comment', '')} for log in logs]
    return result


@endpoint('warehouse.writeoff.read')
def writeoff_catalog_view(request):
    method(request, 'GET')
    warehouses = list(scope(request).prefetch_related('locations').order_by('id'))
    stocks = list(StockInventoryModel.objects.filter(warehouse__in=warehouses, qty__gt=0).select_related('location').prefetch_related('batches').order_by('id'))
    return JsonResponse({'warehouses': [{'id': wh.id, 'name_ru': wh.name_ru, 'name_ky': wh.name_ky, 'name_zh': wh.name_zh,
                                        'locations': [{'id': loc.id, 'code': loc.code} for loc in wh.locations.all()]} for wh in warehouses],
        'skus': [{'id': sku.id, **{key: value for key, value in sku_data(sku).items() if key != 'sku_id'}}
                 for sku in GoodsSKUModel.objects.filter(id__in={stock.sku_id for stock in stocks}).order_by('sku_code')],
        'stock': [{'warehouse_id': stock.warehouse_id, 'sku_id': stock.sku_id, 'location_id': stock.location_id,
                   'location_code': stock.location.code if stock.location else None, 'qty': str(stock.qty),
                   'unbatched_qty': str(stock.qty - sum((batch.qty for batch in stock.batches.all()), Decimal(0))),
                   'batches': [{'batch_no': batch.batch_no, 'expiry_date': batch.expiry_date.isoformat(), 'qty': str(batch.qty)}
                               for batch in stock.batches.all() if batch.qty > 0]} for stock in stocks],
        'permissions': sorted(code for code in request.wms_permissions if code.startswith('warehouse.'))})


@endpoint(lambda request: 'warehouse.writeoff.read' if request.method == 'GET' else 'warehouse.writeoff.manage')
def writeoffs_view(request):
    method(request, 'GET', 'POST')
    if request.method == 'POST':
        with transaction.atomic():
            doc = write_draft(request, parse_json_body(request))
        return JsonResponse({'id': doc.id, 'status': doc.status}, status=201)
    qs = visible(request).select_related('warehouse', 'created_by', 'approved_by', 'posted_by').prefetch_related('items__sku', 'items__location', 'photos')
    if 'warehouse_id' in request.GET:
        qs = qs.filter(warehouse=warehouse(request, request.GET['warehouse_id']))
    if 'id' in request.GET:
        qs = qs.filter(id=integer(request.GET['id']))
    if request.GET.get('status'):
        if request.GET['status'] not in dict(StockWriteoffModel.STATUS):
            raise WmsError('Invalid writeoff status')
        qs = qs.filter(status=request.GET['status'])
    limit = integer(request.GET.get('limit', '50'), high=100)
    offset = integer(request.GET.get('offset', '0'), low=0, high=1000000)
    docs = list(qs.order_by('-id')[offset:offset + limit])
    history = defaultdict(list)
    for log in OperationLogModel.objects.filter(business_type='stock_writeoff', business_id__in=[doc.id for doc in docs]).select_related('actor').order_by('created_at', 'id'):
        history[log.business_id].append(log)
    return JsonResponse({'items': [data(request, doc, history[doc.id]) for doc in docs], 'count': qs.count()})


@endpoint('warehouse.writeoff.manage')
def writeoff_detail_view(request, writeoff_id):
    method(request, 'PATCH')
    with transaction.atomic():
        doc = locked(request, writeoff_id)
        require_action(request, doc, 'edit')
        doc = write_draft(request, parse_json_body(request), doc)
    return JsonResponse({'id': doc.id, 'status': doc.status})


def canonical_photo(upload):
    if upload is None or upload.size > MAX_PHOTO_BYTES or upload.size <= 0:
        raise WmsError('A photo up to 10 MiB is required', 'invalid_photo', 400)
    raw = upload.read(MAX_PHOTO_BYTES + 1)
    if len(raw) > MAX_PHOTO_BYTES:
        raise WmsError('Photo is too large', 'invalid_photo', 400)
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error', Image.DecompressionBombWarning)
            with Image.open(BytesIO(raw)) as image:
                fmt = image.format
                if fmt not in FORMATS or image.width * image.height > MAX_PHOTO_PIXELS or getattr(image, 'n_frames', 1) != 1:
                    raise ValueError('Unsupported image dimensions or format')
                image.verify()
            with Image.open(BytesIO(raw)) as image:
                image.load()
                oriented = ImageOps.exif_transpose(image)
                pixels = oriented.convert('RGBA' if fmt != 'JPEG' and (oriented.mode == 'RGBA' or 'transparency' in oriented.info) else 'RGB')
                output = BytesIO()
                # Canonical pixels only: EXIF, comments and other metadata are not copied.
                clean = Image.new(pixels.mode, pixels.size)
                clean.paste(pixels)
                clean.save(output, format=fmt)
                encoded = output.getvalue()
        if len(encoded) > MAX_PHOTO_BYTES:
            raise ValueError('Canonical image is too large')
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise WmsError('A valid JPEG, PNG or WebP photo up to 20 megapixels is required', 'invalid_photo', 400)
    content_type, extension = FORMATS[fmt]
    try:
        label = get_valid_filename(Path(upload.name.replace('\\', '/')).stem[:200])
    except SuspiciousFileOperation:
        label = 'photo'
    return encoded, content_type, label + extension, extension


@endpoint('warehouse.writeoff.manage')
def writeoff_photos_view(request, writeoff_id):
    method(request, 'POST')
    saved = None
    storage = PrivateMediaStorage()
    try:
        with transaction.atomic():
            doc = locked(request, writeoff_id)
            require_action(request, doc, 'upload_photo')
            if doc.photos.filter(is_active=True).count() >= MAX_PHOTOS:
                raise WmsError('At most five photos are permitted', 'photo_limit', 409)
            try:
                files = request.FILES.getlist('file')
            except MultiPartParserError:
                raise WmsError('Invalid multipart photo', 'invalid_photo', 400)
            if len(files) != 1:
                raise WmsError('Exactly one photo is required per upload', 'invalid_photo', 400)
            encoded, content_type, name, extension = canonical_photo(files[0])
            before = snapshot(doc)
            saved = storage.save('writeoffs/' + uuid4().hex + extension, ContentFile(encoded))
            photo = StockWriteoffPhotoModel.objects.create(writeoff=doc, file_path=saved, file_name=name,
                content_type=content_type, size=len(encoded), uploaded_by_id=request.user_entity.id)
            audit(request, doc, 'photo_uploaded', before)
        return JsonResponse({'id': photo.id, 'file_name': photo.file_name, 'content_type': photo.content_type, 'size': photo.size,
            'download_url': f'/api/warehouse/writeoffs/{doc.id}/photos/{photo.id}/download'}, status=201)
    except Exception:
        # Only a file created by this failing request is removed; existing evidence is untouched.
        if saved:
            storage.delete(saved)
        raise


@endpoint('warehouse.writeoff.manage')
def writeoff_photo_detail_view(request, writeoff_id, photo_id):
    method(request, 'DELETE')
    with transaction.atomic():
        doc = locked(request, writeoff_id)
        require_action(request, doc, 'delete_photo')
        photo = doc.photos.filter(id=photo_id, is_active=True).first()
        if photo is None:
            raise WmsError('Photo not available', 'not_found', 404)
        before = snapshot(doc)
        photo.is_active = False
        photo.save(update_fields=['is_active'])
        audit(request, doc, 'photo_removed', before)
    return JsonResponse({'id': photo.id, 'removed': True})


@endpoint('warehouse.writeoff.read')
def writeoff_photo_download_view(request, writeoff_id, photo_id):
    method(request, 'GET')
    photo = StockWriteoffPhotoModel.objects.filter(id=photo_id, writeoff_id=writeoff_id, is_active=True, writeoff__in=visible(request)).first()
    storage = PrivateMediaStorage()
    if photo is None or not storage.exists(photo.file_path):
        raise WmsError('Photo not available', 'not_found', 404)
    response = FileResponse(storage.open(photo.file_path, 'rb'), as_attachment=True, filename=photo.file_name, content_type=photo.content_type)
    response['X-Content-Type-Options'] = 'nosniff'
    response['Cache-Control'] = 'private, no-store'
    return response


def post_stock(request, doc):
    evidence(doc)
    text(doc.reason, 4000, True)
    lines = list(doc.items.select_related('sku', 'location').order_by('id'))
    if not lines:
        raise WmsError('Writeoff requires items')
    prepared = []
    seen = set()
    for row in lines:
        qty = decimal(row.qty)
        key = (row.sku_id, row.location_id, row.batch_no)
        if not qty or key in seen or (row.location and row.location.warehouse_id != doc.warehouse_id) or bool(row.batch_no) != bool(row.expiry_date):
            raise WmsError('Invalid writeoff line')
        seen.add(key)
        prepared.append(dict(sku=row.sku, location=row.location, qty=qty, batch_no=row.batch_no, expiry_date=row.expiry_date))
    validate_stock(doc.warehouse, prepared)
    for row in lines:
        stock = StockInventoryModel.objects.select_for_update().get(warehouse=doc.warehouse, sku=row.sku, location=row.location)
        if row.batch_no:
            batch = stock.batches.select_for_update().get(batch_no=row.batch_no, expiry_date=row.expiry_date)
            batch.qty -= row.qty
            batch.save(update_fields=['qty'])
        row.unit_cost = decimal(stock.avg_cost, places=2, maximum='999999999999.99')
        row.save(update_fields=['unit_cost'])
        stock.qty = decimal(stock.qty - row.qty)
        stock.save(update_fields=['qty'])
        StockMovementModel.objects.create(warehouse=doc.warehouse, location=row.location, sku=row.sku,
            qty_delta=-row.qty, unit_cost=row.unit_cost, movement_type='issue', source_type='stock_writeoff',
            source_id=doc.id, reason=doc.reason, posted_by_id=request.user_entity.id)
    doc.status = 'posted'
    doc.posted_by_id = request.user_entity.id
    doc.posted_at = timezone.now()
    doc.save(update_fields=['status', 'posted_by', 'posted_at'])


@endpoint(None)
def writeoff_action_view(request, writeoff_id, action):
    method(request, 'POST')
    with transaction.atomic():
        doc = locked(request, writeoff_id)
        if action == 'post' and doc.status == 'posted':
            if 'warehouse.writeoff.post' not in request.wms_permissions:
                raise WmsError('Permission denied', 'permission_denied', 403)
            return JsonResponse({'id': doc.id, 'status': doc.status})
        require_action(request, doc, action)
        before = snapshot(doc)
        comment = ''
        if action == 'submit':
            evidence(doc)
            text(doc.reason, 4000, True)
            if not doc.items.exists():
                raise WmsError('Writeoff requires items')
            doc.status = 'pending_approval'
            doc.save(update_fields=['status'])
        elif action == 'review':
            body = parse_json_body(request)
            decision = body.get('decision')
            if decision not in ('approve', 'return', 'reject'):
                raise WmsError('Invalid review decision')
            comment = text(body.get('comment', ''), 4000, required=decision != 'approve')
            doc.review_comment = comment
            doc.status = {'approve': 'approved', 'return': 'draft', 'reject': 'rejected'}[decision]
            doc.approved_by_id = request.user_entity.id if decision == 'approve' else None
            doc.approved_at = timezone.now() if decision == 'approve' else None
            doc.save(update_fields=['review_comment', 'status', 'approved_by', 'approved_at'])
            action = 'review_' + decision
        elif action == 'post':
            post_stock(request, doc)
        elif action == 'cancel':
            comment = text(parse_json_body(request).get('comment', ''), 4000)
            doc.status = 'cancelled'
            doc.save(update_fields=['status'])
        else:
            raise WmsError('Unknown writeoff action')
        audit(request, doc, action, before, comment)
    return JsonResponse({'id': doc.id, 'status': doc.status})
