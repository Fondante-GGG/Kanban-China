"""Approved two-sided transfers. Physical stock and transit are separate facts."""
from datetime import date
from decimal import Decimal

from django.db import transaction
from django.db.models import Q, Sum
from django.http import JsonResponse
from django.utils import timezone

from backend.infrastructure.persistence.models import (
    GoodsSKUModel, OperationLogModel, StockBatchModel, StockInventoryModel,
    StockMovementModel, StockTransferItemModel, StockTransferModel,
    WarehouseLocationModel, WarehouseModel,
)
from backend.presentation.api.utils import parse_json_body
from backend.presentation.api.warehouse_views import (
    WmsError, balance, decimal, endpoint, integer, lock_warehouses,
    method, rows, scope, sku_data, text, warehouse,
)


def visible(request):
    ids = scope(request).values('id')
    return StockTransferModel.objects.filter(Q(source_warehouse_id__in=ids) | Q(destination_warehouse_id__in=ids))


def is_side(request, transfer, side):
    return request.user_entity.role == 'general_director' or getattr(transfer, side + '_warehouse').manager_id == request.user_entity.id


def actions(request, transfer):
    permissions = request.wms_permissions
    source = is_side(request, transfer, 'source')
    destination = is_side(request, transfer, 'destination')
    result = []
    if source and 'warehouse.transfer.manage' in permissions:
        if transfer.status == 'draft': result.extend(['edit', 'submit'])
        if transfer.status in ('draft', 'pending_approval', 'approved'): result.append('cancel')
    if source and 'warehouse.transfer.approve' in permissions and transfer.created_by_id != request.user_entity.id and transfer.status == 'pending_approval':
        result.append('review')
    if source and 'warehouse.transfer.post' in permissions and transfer.status == 'approved': result.append('dispatch')
    if destination and 'warehouse.transfer.receive' in permissions and transfer.status == 'in_transit': result.append('receive')
    return result


def transfer_data(request, transfer, logs=()):
    data = {
        'id': transfer.id, 'transfer_no': transfer.transfer_no,
        'source_warehouse_id': transfer.source_warehouse_id, 'destination_warehouse_id': transfer.destination_warehouse_id,
        'status': transfer.status, 'comment': transfer.comment, 'review_comment': transfer.review_comment,
        'allowed_actions': actions(request, transfer), 'items': [],
        'created_at': transfer.created_at.isoformat(), 'created_by_name': transfer.created_by.full_name,
        'history': [{'id': log.id, 'action': log.action, 'actor_name': log.actor.full_name if log.actor else '',
                     'created_at': log.created_at.isoformat(), 'comment': log.new_data.get('event_comment', log.new_data.get('comment', ''))} for log in logs],
    }
    for side in ('source', 'destination'):
        wh = getattr(transfer, side + '_warehouse')
        for lang in ('ru', 'ky', 'zh'): data[f'{side}_name_{lang}'] = getattr(wh, 'name_' + lang)
    for stage in ('approved', 'dispatched', 'received'):
        timestamp = getattr(transfer, stage + '_at')
        actor = getattr(transfer, stage + '_by')
        data[stage + '_at'] = timestamp.isoformat() if timestamp else None
        data[stage + '_by_name'] = actor.full_name if actor else None
    transit = transfer.status == 'in_transit'
    total = 0
    for item in transfer.items.all():
        row = {'id': item.id, **sku_data(item.sku), 'qty': item.qty,
               'source_location_id': item.source_location_id, 'destination_location_id': item.destination_location_id,
               'source_location_code': item.source_location.code if item.source_location else None,
               'destination_location_code': item.destination_location.code if item.destination_location else None,
               'batch_no': item.batch_no, 'expiry_date': item.expiry_date.isoformat() if item.expiry_date else None,
               'in_transit_qty': str(item.qty if transit else 0)}
        if 'warehouse.cost.read' in request.wms_permissions and item.unit_cost is not None: row['unit_cost'] = str(item.unit_cost)
        data['items'].append(row)
        total += item.qty if transit else 0
    data['in_transit_qty'] = str(total)
    return data


def detail_qs(request):
    return visible(request).select_related('source_warehouse', 'destination_warehouse', 'created_by', 'approved_by', 'dispatched_by', 'received_by').prefetch_related('items__sku', 'items__source_location', 'items__destination_location')


def get_locked(request, transfer_id):
    found = visible(request).filter(id=transfer_id).first()
    if found is None: raise WmsError('Transfer not available', 'not_found', 404)
    lock_warehouses(found.source_warehouse_id, found.destination_warehouse_id)
    return StockTransferModel.objects.select_for_update().select_related('source_warehouse', 'destination_warehouse').get(id=found.id)


def require_action(request, transfer, action):
    if action not in actions(request, transfer): raise WmsError('Action not permitted for this transfer state or actor', 'permission_denied', 403)


def snapshot(transfer):
    return {'transfer_no': transfer.transfer_no, 'source_warehouse_id': transfer.source_warehouse_id,
            'destination_warehouse_id': transfer.destination_warehouse_id, 'status': transfer.status,
            'comment': transfer.comment, 'review_comment': transfer.review_comment,
            'items': [{'sku_id': row.sku_id, 'qty': row.qty, 'source_location_id': row.source_location_id,
                       'destination_location_id': row.destination_location_id, 'batch_no': row.batch_no,
                       'expiry_date': row.expiry_date.isoformat() if row.expiry_date else None,
                       'unit_cost': str(row.unit_cost) if row.unit_cost is not None else None}
                      for row in transfer.items.order_by('sku_id')]}


def write_draft(request, body, transfer=None):
    before = snapshot(transfer) if transfer is not None else {}
    source = warehouse(request, body.get('source_warehouse_id'))
    destination = WarehouseModel.objects.filter(id=integer(body.get('destination_warehouse_id'))).first()
    if destination is None or source.id == destination.id: raise WmsError('Two different warehouses are required')
    number = text(body.get('transfer_no'), 64, True)
    comment = text(body.get('comment', ''), 4000)
    if transfer is not None and (source.id != transfer.source_warehouse_id or destination.id != transfer.destination_warehouse_id or number != transfer.transfer_no):
        raise WmsError('Transfer route and number are immutable; create a new document')
    creating = transfer is None
    if creating: lock_warehouses(source.id, destination.id)
    prepared = []
    seen = set()
    for row in rows(body):
        sku_id = integer(row.get('sku_id'))
        sku = GoodsSKUModel.objects.filter(id=sku_id, status='active').first()
        if sku is None or sku_id in seen: raise WmsError('Unique active SKU required per transfer')
        seen.add(sku_id)
        qty = integer(row.get('qty'))
        locations = {}
        for side, wh in [('source', source), ('destination', destination)]:
            loc_id = row.get(side + '_location_id')
            loc = WarehouseLocationModel.objects.filter(id=integer(loc_id), warehouse=wh).first() if loc_id is not None else None
            if loc_id is not None and loc is None: raise WmsError('Location belongs to another warehouse')
            locations[side + '_location'] = loc
        batch_no = text(row.get('batch_no', ''), 128)
        expiry = row.get('expiry_date')
        if bool(batch_no) != bool(expiry): raise WmsError('Batch and expiry are required together')
        expiry = date.fromisoformat(expiry) if expiry else None
        stock = StockInventoryModel.objects.filter(warehouse=source, location=locations['source_location'], sku=sku).first()
        if stock is None or stock.qty < qty: raise WmsError('Source inventory is unavailable or insufficient', 'insufficient_stock', 409)
        if batch_no:
            batch = stock.batches.filter(batch_no=batch_no, expiry_date=expiry).first()
            if batch is None or batch.qty < qty: raise WmsError('Batch unavailable or quantity insufficient', 'insufficient_stock', 409)
        else:
            tracked = stock.batches.aggregate(total=Sum('qty'))['total'] or Decimal(0)
            if stock.qty - tracked < qty: raise WmsError('Unbatched stock insufficient; select a batch', 'batch_required', 409)
        prepared.append(dict(sku=sku, qty=qty, batch_no=batch_no, expiry_date=expiry, **locations))
    if transfer is None:
        transfer = StockTransferModel.objects.create(transfer_no=number, source_warehouse=source, destination_warehouse=destination,
                                                     created_by_id=request.user_entity.id, comment=comment)
    else:
        transfer.transfer_no = number; transfer.source_warehouse = source; transfer.destination_warehouse = destination; transfer.comment = comment
        transfer.save(update_fields=['transfer_no', 'source_warehouse', 'destination_warehouse', 'comment'])
        transfer.items.all().delete()
    StockTransferItemModel.objects.bulk_create([StockTransferItemModel(transfer=transfer, **row) for row in prepared])
    OperationLogModel.objects.create(actor_id=request.user_entity.id, action='warehouse.transfer_created' if creating else 'warehouse.transfer_edited',
        business_type='stock_transfer', business_id=transfer.id, old_data=before, new_data=snapshot(transfer), ip_address=request.META.get('REMOTE_ADDR', ''))
    return transfer


@endpoint('warehouse.transfer.read')
def transfer_catalog_view(request):
    method(request, 'GET')
    assigned = list(scope(request).prefetch_related('locations').order_by('id'))
    def warehouse_row(wh):
        return {'id': wh.id, 'name_ru': wh.name_ru, 'name_ky': wh.name_ky, 'name_zh': wh.name_zh,
                'locations': [{'id': loc.id, 'code': loc.code} for loc in wh.locations.all()]}
    stocks = StockInventoryModel.objects.filter(warehouse__in=assigned).select_related('location').prefetch_related('batches').order_by('id')
    stock_data = []
    for item in stocks:
        row = {'warehouse_id': item.warehouse_id, 'sku_id': item.sku_id, 'location_id': item.location_id,
               'location_code': item.location.code if item.location else None, 'qty': str(item.qty),
               'unbatched_qty': str(item.qty - sum((batch.qty for batch in item.batches.all()), Decimal(0))),
               'batches': [{'batch_no': batch.batch_no, 'expiry_date': batch.expiry_date.isoformat(), 'qty': str(batch.qty)} for batch in item.batches.all() if batch.qty > 0]}
        if 'warehouse.cost.read' in request.wms_permissions: row['avg_cost'] = str(item.avg_cost)
        stock_data.append(row)
    return JsonResponse({'sources': [warehouse_row(wh) for wh in assigned],
                         'destinations': [warehouse_row(wh) for wh in WarehouseModel.objects.prefetch_related('locations').order_by('id')] if assigned else [],
                         'skus': [{'id': sku.id, **{k:v for k,v in sku_data(sku).items() if k != 'sku_id'}} for sku in GoodsSKUModel.objects.filter(status='active').order_by('sku_code')] if assigned else [],
                         'stock': stock_data, 'permissions': sorted(p for p in request.wms_permissions if p.startswith('warehouse.'))})


@endpoint(lambda r: 'warehouse.transfer.read' if r.method == 'GET' else 'warehouse.transfer.manage')
def stock_transfers_view(request):
    method(request, 'GET', 'POST')
    if request.method == 'POST':
        with transaction.atomic(): transfer = write_draft(request, parse_json_body(request))
        return JsonResponse({'id': transfer.id, 'status': transfer.status}, status=201)
    qs = detail_qs(request)
    if 'warehouse_id' in request.GET:
        wh = warehouse(request, request.GET['warehouse_id'])
        qs = qs.filter(Q(source_warehouse=wh) | Q(destination_warehouse=wh))
    if 'id' in request.GET: qs = qs.filter(id=integer(request.GET['id']))
    if request.GET.get('status'):
        if request.GET['status'] not in dict(StockTransferModel.STATUS): raise WmsError('Invalid transfer status')
        qs = qs.filter(status=request.GET['status'])
    limit = integer(request.GET.get('limit', '50'), high=100)
    offset = integer(request.GET.get('offset', '0'), low=0, high=1000000)
    transfers = list(qs.order_by('-id')[offset:offset + limit])
    logs_by_id = {}
    for log in OperationLogModel.objects.filter(business_type='stock_transfer', business_id__in=[item.id for item in transfers]).select_related('actor').order_by('created_at', 'id'):
        logs_by_id.setdefault(log.business_id, []).append(log)
    return JsonResponse({'items': [transfer_data(request, item, logs_by_id.get(item.id, ())) for item in transfers], 'count': qs.count()})


@endpoint('warehouse.transfer.manage')
def transfer_detail_view(request, transfer_id):
    method(request, 'PATCH')
    with transaction.atomic():
        transfer = get_locked(request, transfer_id)
        require_action(request, transfer, 'edit')
        transfer = write_draft(request, parse_json_body(request), transfer)
    return JsonResponse({'id': transfer.id, 'status': transfer.status})


@endpoint(None)
def transfer_action_view(request, transfer_id, action):
    method(request, 'POST')
    with transaction.atomic():
        transfer = get_locked(request, transfer_id)
        # Safe retries never create duplicate stock movements or audit events.
        retry = (action == 'dispatch' and transfer.status in ('in_transit', 'received') and transfer.dispatched_at) or (action == 'receive' and transfer.status == 'received' and transfer.received_at)
        if retry:
            side, permission = ('source', 'warehouse.transfer.post') if action == 'dispatch' else ('destination', 'warehouse.transfer.receive')
            if not is_side(request, transfer, side) or permission not in request.wms_permissions: raise WmsError('Permission denied', 'permission_denied', 403)
            return JsonResponse({'id': transfer.id, 'status': transfer.status})
        require_action(request, transfer, action)
        before = snapshot(transfer)
        if action == 'submit':
            if not transfer.items.exists(): raise WmsError('Transfer requires items')
            transfer.status = 'pending_approval'
            transfer.save(update_fields=['status'])
            comment = ''
        elif action == 'review':
            body = parse_json_body(request); decision = body.get('decision')
            if decision not in ('approve', 'return', 'reject'): raise WmsError('Invalid review decision')
            comment = text(body.get('comment', ''), 4000, required=decision != 'approve')
            transfer.review_comment = comment
            transfer.status = {'approve':'approved', 'return':'draft', 'reject':'rejected'}[decision]
            transfer.approved_by_id = request.user_entity.id if decision == 'approve' else None
            transfer.approved_at = timezone.now() if decision == 'approve' else None
            transfer.save(update_fields=['status', 'review_comment', 'approved_by', 'approved_at'])
            action = 'review_' + decision
        elif action == 'cancel':
            comment = text(parse_json_body(request).get('comment', ''), 4000)
            transfer.status = 'cancelled'; transfer.save(update_fields=['status'])
        elif action == 'dispatch':
            dispatch(request, transfer); comment = ''
        elif action == 'receive':
            receive(request, transfer); comment = ''
        else: raise WmsError('Unknown action')
        OperationLogModel.objects.create(actor_id=request.user_entity.id, action='warehouse.transfer_' + action, business_type='stock_transfer',
            business_id=transfer.id, old_data=before, new_data={**snapshot(transfer), 'event_comment': comment}, ip_address=request.META.get('REMOTE_ADDR', ''))
    return JsonResponse({'id': transfer.id, 'status': transfer.status})


def dispatch(request, transfer):
    lines = list(transfer.items.select_related('sku', 'source_location').order_by('sku_id'))
    if not lines: raise WmsError('Transfer requires items')
    for row in lines:
        integer(row.qty)
        if bool(row.batch_no) != bool(row.expiry_date): raise WmsError('Invalid batch metadata')
        stock = StockInventoryModel.objects.select_for_update().filter(warehouse=transfer.source_warehouse, location=row.source_location, sku=row.sku).first()
        if stock is None or stock.qty < row.qty: raise WmsError('Insufficient source inventory', 'insufficient_stock', 409)
        if row.source_location and row.source_location.warehouse_id != transfer.source_warehouse_id: raise WmsError('Invalid source location')
        if row.batch_no:
            batch = stock.batches.select_for_update().filter(batch_no=row.batch_no, expiry_date=row.expiry_date).first()
            if batch is None or batch.qty < row.qty: raise WmsError('Insufficient batch inventory', 'insufficient_stock', 409)
            batch.qty -= row.qty; batch.save(update_fields=['qty'])
        else:
            tracked = stock.batches.aggregate(total=Sum('qty'))['total'] or Decimal(0)
            if stock.qty - tracked < row.qty: raise WmsError('A batch must be selected for tracked stock', 'batch_required', 409)
        decimal(stock.qty - row.qty)
        row.unit_cost = decimal(stock.avg_cost, places=2, maximum='999999999999.99'); row.save(update_fields=['unit_cost'])
        stock.qty -= row.qty; stock.save(update_fields=['qty'])
        StockMovementModel.objects.create(warehouse=transfer.source_warehouse, location=row.source_location, sku=row.sku,
            qty_delta=-row.qty, unit_cost=row.unit_cost, movement_type='transfer_out', source_type='stock_transfer', source_id=transfer.id, posted_by_id=request.user_entity.id)
    transfer.status='in_transit'; transfer.dispatched_by_id=request.user_entity.id; transfer.dispatched_at=timezone.now()
    transfer.save(update_fields=['status','dispatched_by','dispatched_at'])


def receive(request, transfer):
    lines = list(transfer.items.select_related('sku', 'destination_location').order_by('sku_id'))
    if not lines: raise WmsError('Transfer requires items')
    for row in lines:
        integer(row.qty)
        if row.unit_cost is None: raise WmsError('Dispatch cost is missing', 'conflict', 409)
        if row.destination_location and row.destination_location.warehouse_id != transfer.destination_warehouse_id: raise WmsError('Invalid destination location')
        stock=balance(transfer.destination_warehouse, row.sku, row.destination_location)
        qty=decimal(stock.qty + row.qty)
        cost = decimal((((stock.qty * stock.avg_cost) + (row.qty * row.unit_cost)) / qty).quantize(Decimal('0.01')), places=2, maximum='999999999999.99')
        stock.avg_cost=cost; stock.qty=qty; stock.save(update_fields=['qty','avg_cost'])
        if row.batch_no:
            batch,_=StockBatchModel.objects.select_for_update().get_or_create(inventory=stock,batch_no=row.batch_no,defaults={'expiry_date':row.expiry_date,'qty':0})
            if batch.expiry_date != row.expiry_date: raise WmsError('Destination batch expiry mismatch', 'batch_conflict', 409)
            batch.qty=decimal(batch.qty+row.qty);batch.save(update_fields=['qty'])
        StockMovementModel.objects.create(warehouse=transfer.destination_warehouse,location=row.destination_location,sku=row.sku,
            qty_delta=row.qty,unit_cost=row.unit_cost,movement_type='transfer_in',source_type='stock_transfer',source_id=transfer.id,posted_by_id=request.user_entity.id)
    transfer.status='received';transfer.received_by_id=request.user_entity.id;transfer.received_at=timezone.now()
    transfer.save(update_fields=['status','received_by','received_at'])


@endpoint('warehouse.transfer.post')
def post_stock_transfer_view(request, transfer_id):
    method(request, 'POST')
    raise WmsError('Direct posting retired; use submit, review, dispatch and receive', 'legacy_endpoint_retired', 410)
