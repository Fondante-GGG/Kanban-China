"""Receipt-bound supplier returns with atomic stock and finance review records."""
from collections import defaultdict
from decimal import Decimal
from uuid import uuid4

from django.core.files.base import ContentFile
from django.http import FileResponse, HttpRequest, JsonResponse
from django.http.multipartparser import MultiPartParserError
from django.db import transaction
from django.db.models import Q, Sum
from django.utils import timezone

from backend.infrastructure.persistence.models import (
    OperationLogModel, StockInventoryModel,
    PurchaseReceiptModel, SupplierReturnFinanceReviewModel,
    NotificationModel, UserModel,
    StockMovementModel, SupplierReturnModel, SupplierReturnItemModel,
    SupplierReturnPhotoModel,
)
from backend.infrastructure.persistence.storage import PrivateMediaStorage
from backend.presentation.api.utils import parse_json_body
from backend.presentation.api.warehouse_writeoff_views import canonical_photo
from backend.presentation.api.warehouse_views import (
    WmsError, decimal, endpoint, integer, lock_warehouses, method, rows,
    scope, sku_data, text, warehouse, wh_data,
)

MAX_PHOTOS = 5


def visible(request):
    return SupplierReturnModel.objects.filter(warehouse__in=scope(request))


def actions(request: HttpRequest, doc: SupplierReturnModel) -> list[str]:
    result = []
    if 'warehouse.return.manage' in request.wms_permissions:
        if doc.status == 'draft':
            result.extend(['edit', 'upload_photo', 'delete_photo', 'submit'])
        if doc.status in ('draft', 'pending_approval', 'approved'):
            result.append('cancel')
    if ('warehouse.return.approve' in request.wms_permissions and doc.status == 'pending_approval'
            and doc.created_by_id != request.user_entity.id):
        result.append('review')
    if 'warehouse.return.post' in request.wms_permissions and doc.status == 'approved':
        result.append('post')
    return result


def require_action(request: HttpRequest, doc: SupplierReturnModel, action: str) -> None:
    if action not in actions(request, doc):
        raise WmsError('Action not permitted for this document or actor', 'permission_denied', 403)


def locked(request, doc_id):
    found = visible(request).filter(id=doc_id).first()
    if found is None:
        raise WmsError('Return not available', 'not_found', 404)
    lock_warehouses(found.warehouse_id)
    return SupplierReturnModel.objects.select_for_update().select_related('warehouse').get(id=found.id)


def snapshot(doc):
    return {'return_no': doc.return_no, 'receipt_id': doc.receipt_id,
            'warehouse_id': doc.warehouse_id, 'reason_type': doc.reason_type,
            'reason': doc.reason, 'status': doc.status, 'review_comment': doc.review_comment,
            'items': [{'receipt_item_id': row.receipt_item_id, 'qty': row.qty,
                       'unit_cost': str(row.unit_cost) if row.unit_cost is not None else None}
                      for row in doc.items.order_by('id')],
            'photos': [{'id': photo.id, 'file_name': photo.file_name, 'is_active': photo.is_active}
                       for photo in doc.photos.order_by('id')]}


def audit(request, doc, action, before, comment=''):
    OperationLogModel.objects.create(actor_id=request.user_entity.id, action='warehouse.return_' + action,
        business_type='supplier_return', business_id=doc.id, old_data=before,
        new_data={**snapshot(doc), 'event_comment': comment}, ip_address=request.META.get('REMOTE_ADDR', ''))


def photos_required(doc: SupplierReturnModel) -> bool:
    return doc.reason_type in ('damage', 'expiry') or doc.items.filter(
        receipt_item__expiry_date__lt=timezone.localdate()).exists()


def evidence(doc: SupplierReturnModel) -> None:
    required = photos_required(doc)
    photos = list(doc.photos.filter(is_active=True))
    storage = PrivateMediaStorage()
    if (required and not photos) or any(not storage.exists(photo.file_path) for photo in photos):
        raise WmsError('Photo evidence is required and every attached file must be available', 'photo_required', 409)


def prepared_lines(doc: SupplierReturnModel) -> list[SupplierReturnItemModel]:
    lines = list(doc.items.select_related('receipt_item__po_item__sku', 'receipt_item__location').order_by('id'))
    if not lines:
        raise WmsError('Return requires items')
    return lines


def validate_lines(doc: SupplierReturnModel, lines: list[SupplierReturnItemModel]) -> None:
    """Warehouse lock protects cumulative receipt limit and every stock writer."""
    if doc.receipt.status != 'posted' or doc.warehouse_id != doc.receipt.warehouse_id:
        raise WmsError('Return source is not a posted receipt', 'conflict', 409)
    grouped = defaultdict(lambda: Decimal(0))
    for line in lines:
        source = line.receipt_item
        if source.receipt_id != doc.receipt_id or not integer(line.qty):
            raise WmsError('Invalid return receipt line')
        if source.location_id and source.location.warehouse_id != doc.warehouse_id:
            raise WmsError('Source location belongs to another warehouse')
        used = SupplierReturnItemModel.objects.filter(receipt_item=source,
            supplier_return__status='posted').exclude(supplier_return=doc).aggregate(total=Sum('qty'))['total'] or 0
        if line.qty + used > source.qty:
            raise WmsError('Return exceeds original accepted quantity', 'receipt_limit', 409)
        grouped[(source.po_item.sku_id, source.location_id, source.batch_no, source.expiry_date)] += line.qty
    stocks = {}
    for (sku_id, loc_id, batch_no, expiry), qty in grouped.items():
        key = (sku_id, loc_id)
        if key not in stocks:
            stock = StockInventoryModel.objects.select_for_update().filter(
                warehouse_id=doc.warehouse_id, sku_id=sku_id, location_id=loc_id).first()
            if stock is None:
                raise WmsError('Source inventory is insufficient', 'insufficient_stock', 409)
            stocks[key] = stock
        stock = stocks[key]
        total = sum(value for (sku, loc, _, _), value in grouped.items() if (sku, loc) == key)
        if total > stock.qty:
            raise WmsError('Source inventory is insufficient', 'insufficient_stock', 409)
        batches = list(stock.batches.select_for_update().all())
        if batch_no:
            batch = next((row for row in batches if row.batch_no == batch_no and row.expiry_date == expiry), None)
            if batch is None or qty > batch.qty:
                raise WmsError('Source batch is insufficient', 'insufficient_stock', 409)
        elif qty > stock.qty - sum((row.qty for row in batches), Decimal(0)):
            raise WmsError('Source unbatched inventory is insufficient', 'insufficient_stock', 409)


def write_draft(request, body, doc=None):
    receipt = PurchaseReceiptModel.objects.select_related('warehouse', 'purchase_order__supplier').filter(
        id=integer(body.get('receipt_id')), warehouse__in=scope(request), status='posted').first()
    if receipt is None:
        raise WmsError('Posted receipt not available', 'not_found', 404)
    number = text(body.get('return_no'), 64, True)
    reason = text(body.get('reason'), 4000, True)
    reason_type = body.get('reason_type')
    if reason_type not in ('damage', 'expiry', 'other'):
        raise WmsError('Invalid return reason type')
    if doc and (doc.receipt_id != receipt.id or doc.return_no != number):
        raise WmsError('Return number and receipt are immutable')
    lock_warehouses(receipt.warehouse_id)
    before = snapshot(doc) if doc else {}
    prepared, seen = [], set()
    for row in rows(body):
        source_id = integer(row.get('receipt_item_id'))
        source = receipt.items.filter(id=source_id).first()
        if source is None or source_id in seen:
            raise WmsError('Invalid or duplicate receipt item')
        seen.add(source_id)
        prepared.append(dict(receipt_item=source, qty=integer(row.get('qty'))))
    creating = doc is None
    if creating:
        doc = SupplierReturnModel.objects.create(return_no=number, receipt=receipt, warehouse=receipt.warehouse,
            reason_type=reason_type, reason=reason, created_by_id=request.user_entity.id)
    else:
        doc.reason, doc.reason_type = reason, reason_type
        doc.save(update_fields=['reason', 'reason_type'])
        doc.items.all().delete()
    SupplierReturnItemModel.objects.bulk_create([SupplierReturnItemModel(supplier_return=doc, **row) for row in prepared])
    validate_lines(doc, prepared_lines(doc))
    audit(request, doc, 'created' if creating else 'edited', before)
    return doc


def data(request, doc, logs=()):
    supplier = doc.receipt.purchase_order.supplier
    result = {'id': doc.id, 'return_no': doc.return_no, 'receipt_id': doc.receipt_id,
        'receipt_no': doc.receipt.receipt_no, 'supplier_id': supplier.id, 'supplier_name': supplier.name_ru,
        **wh_data(doc.warehouse), 'status': doc.status, 'reason_type': doc.reason_type,
        'reason': doc.reason, 'review_comment': doc.review_comment, 'created_at': doc.created_at.isoformat(),
        'created_by_name': doc.created_by.full_name, 'allowed_actions': actions(request, doc),
        'photos_required': photos_required(doc),
        'finance_review_status': 'pending' if doc.status == 'posted' else None, 'items': [], 'photos': [], 'history': []}
    for stage in ('approved', 'posted'):
        actor, stamp = getattr(doc, stage + '_by'), getattr(doc, stage + '_at')
        result[stage + '_by_name'] = actor.full_name if actor else None
        result[stage + '_at'] = stamp.isoformat() if stamp else None
    for item in doc.items.all():
        source = item.receipt_item
        row = {'id': item.id, 'receipt_item_id': source.id, **sku_data(source.po_item.sku),
               'location_id': source.location_id, 'location_code': source.location.code if source.location else None,
               'qty': str(item.qty), 'batch_no': source.batch_no,
               'expiry_date': source.expiry_date.isoformat() if source.expiry_date else None}
        if 'warehouse.cost.read' in request.wms_permissions and item.unit_cost is not None:
            row['unit_cost'] = str(item.unit_cost)
        result['items'].append(row)
    result['photos'] = [{'id': photo.id, 'file_name': photo.file_name, 'content_type': photo.content_type, 'size': photo.size,
                         'download_url': f'/api/warehouse/returns/{doc.id}/photos/{photo.id}/download'}
                        for photo in doc.photos.all() if photo.is_active]
    result['history'] = [{'id': log.id, 'action': log.action, 'actor_name': log.actor.full_name if log.actor else '',
                          'created_at': log.created_at.isoformat(), 'comment': log.new_data.get('event_comment', '')} for log in logs]
    return result




@endpoint('warehouse.return.read')
def return_catalog_view(request):
    method(request, 'GET')
    warehouses = list(scope(request).order_by('id'))
    receipts = PurchaseReceiptModel.objects.filter(warehouse__in=warehouses, status='posted').select_related(
        'purchase_order__supplier').prefetch_related('items__po_item__sku', 'items__location').order_by('-id')
    if 'warehouse_id' in request.GET:
        receipts = receipts.filter(warehouse=warehouse(request, request.GET['warehouse_id']))
    if request.GET.get('q'):
        receipts = receipts.filter(receipt_no__icontains=text(request.GET['q'], 64))
    if 'receipt_id' in request.GET:
        receipts = receipts.filter(id=integer(request.GET['receipt_id']))
    limit = integer(request.GET.get('limit', '50'), high=100)
    offset = integer(request.GET.get('offset', '0'), low=0, high=1000000)
    count = receipts.count()
    receipts = list(receipts[offset:offset+limit])
    source_ids = [row.id for receipt in receipts for row in receipt.items.all()]
    returned_by_source = dict(SupplierReturnItemModel.objects.filter(
        receipt_item_id__in=source_ids, supplier_return__status='posted').values('receipt_item_id')
        .annotate(total=Sum('qty')).values_list('receipt_item_id', 'total'))
    entries = []
    for receipt in receipts:
        items = []
        for row in receipt.items.all():
            returned = returned_by_source.get(row.id, 0)
            items.append({'receipt_item_id': row.id, **sku_data(row.po_item.sku),
                'location_id': row.location_id, 'location_code': row.location.code if row.location else None,
                'batch_no': row.batch_no, 'expiry_date': row.expiry_date.isoformat() if row.expiry_date else None,
                'received_qty': row.qty, 'returned_qty': returned, 'returnable_qty': max(0, row.qty-returned)})
        supplier = receipt.purchase_order.supplier
        entries.append({'id': receipt.id, 'receipt_no': receipt.receipt_no, 'warehouse_id': receipt.warehouse_id,
            'supplier_id': supplier.id, 'supplier_name': supplier.name_ru, 'items': items})
    return JsonResponse({'warehouses': [{'id': wh.id, 'name_ru': wh.name_ru, 'name_ky': wh.name_ky, 'name_zh': wh.name_zh}
                                       for wh in warehouses], 'receipts': entries, 'receipt_count': count, 'limit': limit, 'offset': offset,
        'permissions': sorted(code for code in request.wms_permissions if code.startswith('warehouse.'))})




@endpoint(lambda request: 'warehouse.return.read' if request.method == 'GET' else 'warehouse.return.manage')
def returns_view(request):
    method(request, 'GET', 'POST')
    if request.method == 'POST':
        with transaction.atomic():
            doc = write_draft(request, parse_json_body(request))
        return JsonResponse({'id': doc.id, 'status': doc.status}, status=201)
    qs = visible(request).select_related('warehouse', 'receipt__purchase_order__supplier', 'created_by', 'approved_by', 'posted_by').prefetch_related('items__receipt_item__po_item__sku', 'items__receipt_item__location', 'photos')
    if 'warehouse_id' in request.GET:
        qs = qs.filter(warehouse=warehouse(request, request.GET['warehouse_id']))
    if 'id' in request.GET:
        qs = qs.filter(id=integer(request.GET['id']))
    if request.GET.get('status'):
        if request.GET['status'] not in dict(SupplierReturnModel.STATUS):
            raise WmsError('Invalid supplier_return status')
        qs = qs.filter(status=request.GET['status'])
    limit = integer(request.GET.get('limit', '50'), high=100)
    offset = integer(request.GET.get('offset', '0'), low=0, high=1000000)
    docs = list(qs.order_by('-id')[offset:offset + limit])
    history = defaultdict(list)
    for log in OperationLogModel.objects.filter(business_type='supplier_return', business_id__in=[doc.id for doc in docs]).select_related('actor').order_by('created_at', 'id'):
        history[log.business_id].append(log)
    return JsonResponse({'items': [data(request, doc, history[doc.id]) for doc in docs], 'count': qs.count()})


@endpoint('warehouse.return.manage')
def return_detail_view(request, return_id):
    method(request, 'PATCH')
    with transaction.atomic():
        doc = locked(request, return_id)
        require_action(request, doc, 'edit')
        doc = write_draft(request, parse_json_body(request), doc)
    return JsonResponse({'id': doc.id, 'status': doc.status})




@endpoint('warehouse.return.manage')
def return_photos_view(request, return_id):
    method(request, 'POST')
    saved = None
    storage = PrivateMediaStorage()
    try:
        with transaction.atomic():
            doc = locked(request, return_id)
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
            saved = storage.save('returns/' + uuid4().hex + extension, ContentFile(encoded))
            photo = SupplierReturnPhotoModel.objects.create(supplier_return=doc, file_path=saved, file_name=name,
                content_type=content_type, size=len(encoded), uploaded_by_id=request.user_entity.id)
            audit(request, doc, 'photo_uploaded', before)
        return JsonResponse({'id': photo.id, 'file_name': photo.file_name, 'content_type': photo.content_type, 'size': photo.size,
            'download_url': f'/api/warehouse/returns/{doc.id}/photos/{photo.id}/download'}, status=201)
    except Exception:
        # Only a file created by this failing request is removed; existing evidence is untouched.
        if saved:
            storage.delete(saved)
        raise


@endpoint('warehouse.return.manage')
def return_photo_detail_view(request, return_id, photo_id):
    method(request, 'DELETE')
    with transaction.atomic():
        doc = locked(request, return_id)
        require_action(request, doc, 'delete_photo')
        photo = doc.photos.filter(id=photo_id, is_active=True).first()
        if photo is None:
            raise WmsError('Photo not available', 'not_found', 404)
        before = snapshot(doc)
        photo.is_active = False
        photo.save(update_fields=['is_active'])
        audit(request, doc, 'photo_removed', before)
    return JsonResponse({'id': photo.id, 'removed': True})


@endpoint('warehouse.return.read')
def return_photo_download_view(request, return_id, photo_id):
    method(request, 'GET')
    photo = SupplierReturnPhotoModel.objects.filter(id=photo_id, supplier_return_id=return_id, is_active=True, supplier_return__in=visible(request)).first()
    storage = PrivateMediaStorage()
    if photo is None or not storage.exists(photo.file_path):
        raise WmsError('Photo not available', 'not_found', 404)
    response = FileResponse(storage.open(photo.file_path, 'rb'), as_attachment=True, filename=photo.file_name, content_type=photo.content_type)
    response['X-Content-Type-Options'] = 'nosniff'
    response['Cache-Control'] = 'private, no-store'
    return response


def post_stock(request: HttpRequest, doc: SupplierReturnModel) -> None:
    evidence(doc)
    text(doc.reason, 4000, True)
    lines = prepared_lines(doc)
    validate_lines(doc, lines)
    for row in lines:
        source = row.receipt_item
        stock = StockInventoryModel.objects.select_for_update().get(warehouse=doc.warehouse,
            sku_id=source.po_item.sku_id, location_id=source.location_id)
        if source.batch_no:
            batch = stock.batches.select_for_update().get(batch_no=source.batch_no, expiry_date=source.expiry_date)
            batch.qty -= row.qty
            batch.save(update_fields=['qty'])
        row.unit_cost = decimal(stock.avg_cost, places=2, maximum='999999999999.99')
        row.save(update_fields=['unit_cost'])
        stock.qty = decimal(stock.qty - row.qty)
        stock.save(update_fields=['qty'])
        StockMovementModel.objects.create(warehouse=doc.warehouse, location_id=source.location_id,
            sku_id=source.po_item.sku_id, qty_delta=-row.qty, unit_cost=row.unit_cost,
            movement_type='issue', source_type='supplier_return', source_id=doc.id,
            reason=doc.reason, posted_by_id=request.user_entity.id)
    doc.status, doc.posted_by_id, doc.posted_at = 'posted', request.user_entity.id, timezone.now()
    doc.save(update_fields=['status', 'posted_by', 'posted_at'])
    SupplierReturnFinanceReviewModel.objects.create(supplier_return=doc)
    # Same-DB durable delivery: failure rolls back stock, review and audit together.
    recipients = UserModel.objects.filter(is_active=True).filter(
        Q(role='general_director') | Q(system_role_links__role__is_active=True,
            system_role_links__role__permissions__code='finance.payable.read')).distinct()
    for user in recipients.iterator():
        title = {'ru': 'Возврат поставщику требует проверки финансов',
                 'ky': 'Жеткирүүчүгө кайтаруу каржы текшерүүсүн талап кылат',
                 'zh': '供应商退货需要财务审核', 'zh-CN': '供应商退货需要财务审核',
                 'zh-TW': '供應商退貨需要財務審核',
                 'zh-Hans': '供应商退货需要财务审核', 'zh-Hant': '供應商退貨需要財務審核'}.get(user.interface_language,
                     'Возврат поставщику требует проверки финансов')
        NotificationModel.objects.create(user=user, title=title,
            message=doc.return_no, entity_type='supplier_return', entity_id=doc.id)


@endpoint(None)
def return_action_view(request, return_id, action):
    method(request, 'POST')
    with transaction.atomic():
        doc = locked(request, return_id)
        if action == 'post' and doc.status == 'posted':
            if 'warehouse.return.post' not in request.wms_permissions:
                raise WmsError('Permission denied', 'permission_denied', 403)
            return JsonResponse({'id': doc.id, 'status': doc.status})
        require_action(request, doc, action)
        before = snapshot(doc)
        comment = ''
        if action == 'submit':
            evidence(doc)
            text(doc.reason, 4000, True)
            validate_lines(doc, prepared_lines(doc))
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
            raise WmsError('Unknown supplier_return action')
        audit(request, doc, action, before, comment)
    return JsonResponse({'id': doc.id, 'status': doc.status})


@endpoint('finance.payable.read')
def finance_supplier_returns_view(request):
    """Read-only accounting queue; no implied credit or period adjustment."""
    method(request, 'GET')
    qs = SupplierReturnFinanceReviewModel.objects.select_related(
        'supplier_return__receipt__purchase_order__supplier').prefetch_related(
        'supplier_return__items__receipt_item__po_item__sku', 'supplier_return__photos').order_by('-id')
    if 'return_id' in request.GET:
        qs = qs.filter(supplier_return_id=integer(request.GET['return_id']))
    limit = integer(request.GET.get('limit', '50'), high=100)
    offset = integer(request.GET.get('offset', '0'), low=0, high=1000000)
    result = []
    for review in qs[offset:offset+limit]:
        doc = review.supplier_return
        order = doc.receipt.purchase_order
        items = [{'receipt_item_id': row.receipt_item_id, **sku_data(row.receipt_item.po_item.sku),
                  'qty': str(row.qty), 'unit_cost': str(row.unit_cost)} for row in doc.items.all()]
        valuation = sum((row.qty * row.unit_cost for row in doc.items.all()), Decimal(0))
        result.append({'id': review.id, 'return_id': doc.id, 'return_no': doc.return_no,
            'receipt_id': doc.receipt_id, 'receipt_no': doc.receipt.receipt_no,
            'supplier_id': order.supplier_id, 'supplier_name': order.supplier.name_ru,
            'warehouse_id': doc.warehouse_id, 'status': review.status,
            'created_at': review.created_at.isoformat(), 'posted_at': doc.posted_at.isoformat(),
            'source_currency': order.currency, 'valuation_currency': None,
            'valuation_status': 'currency_unresolved', 'stock_valuation': str(valuation), 'items': items,
            'photos': [{'id': photo.id, 'file_name': photo.file_name, 'content_type': photo.content_type,
                'size': photo.size, 'download_url': f'/api/finance/supplier-returns/{review.id}/photos/{photo.id}/download'}
                for photo in doc.photos.all() if photo.is_active]})
    return JsonResponse({'items': result, 'count': qs.count()})


@endpoint('finance.payable.read')
def finance_supplier_return_photo_view(request, review_id, photo_id):
    """Financial evidence access does not grant source warehouse access."""
    method(request, 'GET')
    review = SupplierReturnFinanceReviewModel.objects.filter(id=review_id).first()
    photo = SupplierReturnPhotoModel.objects.filter(id=photo_id,
        supplier_return_id=review.supplier_return_id, is_active=True).first() if review else None
    storage = PrivateMediaStorage()
    if photo is None or not storage.exists(photo.file_path):
        raise WmsError('Photo not available', 'not_found', 404)
    response = FileResponse(storage.open(photo.file_path, 'rb'), as_attachment=True,
        filename=photo.file_name, content_type=photo.content_type)
    response['X-Content-Type-Options'] = 'nosniff'
    response['Cache-Control'] = 'private, no-store'
    return response
