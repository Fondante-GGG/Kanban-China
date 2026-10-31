import json
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch

from django.test import Client, TestCase
from backend.domain.entities import User
from backend.infrastructure.di.container import container
from backend.infrastructure.persistence.models import (
    DepartmentModel, UserModel, SystemRoleModel, SystemPermissionModel, UserSystemRoleModel,
    WarehouseModel, WarehouseLocationModel, GoodsSKUModel, SupplierModel, PurchaseOrderModel,
    PurchaseOrderItemModel, PurchaseReceiptModel, PurchaseReceiptItemModel, StockInventoryModel,
    StockMovementModel, StockCountModel, StockCountItemModel, StockTransferModel,
    StockTransferItemModel, StockBatchModel, OperationLogModel, GoodsCertificateModel,
)


class WarehouseScopeTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.dept = DepartmentModel.objects.create(name="WMS")
        self.other_dept = DepartmentModel.objects.create(name="Foreign")
        self.user = UserModel.objects.create_user(email="wms@test", password="password123", full_name="Warehouse employee", role="employee", department=self.dept)
        self.director = UserModel.objects.create_user(email="wms.director@test", password="password123", full_name="Director", role="general_director", department=self.dept)
        self.wh = WarehouseModel.objects.create(name_ru="Own", manager=self.user)
        self.foreign = WarehouseModel.objects.create(name_ru="Foreign")
        self.location = WarehouseLocationModel.objects.create(warehouse=self.wh, code="A1")
        self.foreign_location = WarehouseLocationModel.objects.create(warehouse=self.foreign, code="Secret")
        self.sku = GoodsSKUModel.objects.create(sku_code="WMS-1", name_ru="Own SKU", status="active", created_by=self.director)
        self.sku2 = GoodsSKUModel.objects.create(sku_code="WMS-2", name_ru="Second SKU", status="active", created_by=self.director)
        self.supplier = SupplierModel.objects.create(name_ru="Supplier", created_by=self.director)
        self.order = PurchaseOrderModel.objects.create(po_no="WMS-PO", supplier=self.supplier, department=self.dept, status="approved", order_date=date.today(), created_by=self.director)
        self.line = PurchaseOrderItemModel.objects.create(purchase_order=self.order, sku=self.sku, ordered_qty=10, unit_price="12.50")
        self.foreign_order = PurchaseOrderModel.objects.create(po_no="SECRET-PO", supplier=self.supplier, department=self.other_dept, status="approved", order_date=date.today(), created_by=self.director)
        self.role = SystemRoleModel.objects.create(code="wms_test", name="WMS")
        for code in ["warehouse.inventory.read", "warehouse.receipt.read", "warehouse.receipt.manage", "warehouse.receipt.post", "warehouse.count.read", "warehouse.count.manage", "warehouse.count.approve", "warehouse.transfer.read", "warehouse.transfer.manage", "warehouse.transfer.post", "warehouse.transfer.receive"]:
            permission, _ = SystemPermissionModel.objects.get_or_create(code=code, defaults={"name": code})
            self.role.permissions.add(permission)
        UserSystemRoleModel.objects.create(user=self.user, role=self.role)

    def headers(self, user=None):
        user = user or self.user
        entity = User(id=user.id, email=user.email, password_hash=user.password, full_name=user.full_name, role=user.role, department_id=user.department_id)
        return {"HTTP_AUTHORIZATION": f"Bearer {container.jwt_service.generate_token(entity)}"}

    def post(self, path, payload=None, user=None):
        return self.client.post('/api/warehouse/' + path, data=json.dumps(payload or {}), content_type="application/json", **self.headers(user))

    def receipt(self, number="WMS-REC", wh=None):
        receipt = PurchaseReceiptModel.objects.create(receipt_no=number, warehouse=wh or self.wh, purchase_order=self.order, received_by=self.user)
        PurchaseReceiptItemModel.objects.create(receipt=receipt, po_item=self.line, qty=10, unit_cost="12.50")
        return receipt

    def test_catalog_stock_ledger_and_alerts_are_scoped_and_costs_hidden(self):
        stock = StockInventoryModel.objects.create(warehouse=self.wh, sku=self.sku, qty=3, avg_cost=12)
        secret = StockInventoryModel.objects.create(warehouse=self.foreign, sku=self.sku2, qty=9, avg_cost=99)
        for inv in [stock, secret]:
            StockMovementModel.objects.create(warehouse=inv.warehouse, sku=inv.sku, qty_delta=inv.qty, unit_cost=inv.avg_cost, movement_type="receipt", source_type="purchase_receipt", source_id=1, posted_by=self.director)
            StockBatchModel.objects.create(inventory=inv, batch_no="B", expiry_date=date.today()+timedelta(days=1), qty=inv.qty)
            GoodsCertificateModel.objects.create(sku=inv.sku, number="C", expires_at=date.today(), created_by=self.director)
        catalog = self.client.get('/api/warehouse/catalog', **self.headers()).json()
        self.assertEqual([x['id'] for x in catalog['warehouses']], [self.wh.id])
        self.assertEqual([x['id'] for x in catalog['purchase_orders']], [self.order.id])
        self.assertNotIn('unit_cost', catalog['purchase_orders'][0]['items'][0])
        for path in ['inventory', 'movements']:
            response = self.client.get('/api/warehouse/' + path, **self.headers())
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()['count'], 1)
            self.assertEqual(response.json()['items'][0]['warehouse_id'], self.wh.id)
            self.assertNotIn('avg_cost', response.json()['items'][0]); self.assertNotIn('unit_cost', response.json()['items'][0])
            self.assertEqual(self.client.get('/api/warehouse/'+path, {'warehouse_id':self.foreign.id}, **self.headers()).status_code, 403)
        alerts = self.client.get('/api/warehouse/alerts/expiry', **self.headers()).json()
        self.assertEqual([b['warehouse_id'] for b in alerts['batches']], [self.wh.id])
        self.assertEqual([c['sku_id'] for c in alerts['certificates']], [self.sku.id])
        permission, _ = SystemPermissionModel.objects.get_or_create(code="warehouse.cost.read", defaults={"name":"Cost"}); self.role.permissions.add(permission)
        self.assertIn('avg_cost', self.client.get('/api/warehouse/inventory', **self.headers()).json()['items'][0])
        self.assertIn('unit_cost', self.client.get('/api/warehouse/movements', **self.headers()).json()['items'][0])

    def test_receipt_creation_derives_cost_and_rejects_foreign_ids_atomically(self):
        body = {"receipt_no":"CREATE", "warehouse_id":self.wh.id, "purchase_order_id":self.order.id, "items":[{"po_item_id":self.line.id,"qty":10}]}
        response = self.post('receipts', body)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(PurchaseReceiptItemModel.objects.get(receipt_id=response.json()['id']).unit_cost, Decimal(self.line.unit_price))
        listing = self.client.get('/api/warehouse/receipts', **self.headers()).json()['items'][0]
        self.assertNotIn('unit_cost', listing['items'][0]); self.assertEqual(listing['allowed_actions'], ['post'])
        for key, value in [('warehouse_id', self.foreign.id), ('purchase_order_id', self.foreign_order.id)]:
            invalid = {**body, "receipt_no":key, key:value}
            self.assertEqual(self.post('receipts', invalid).status_code, 403)
        for row, status in [({"po_item_id":self.line.id,"qty":10,"unit_cost":"0"},403), ({"po_item_id":self.line.id,"qty":10,"location_id":self.foreign_location.id},400), ({"po_item_id":self.line.id,"qty":1.2},400)]:
            self.assertEqual(self.post('receipts', {**body,"receipt_no":"INVALID","items":[row]}).status_code, status)
            self.assertFalse(PurchaseReceiptModel.objects.filter(receipt_no="INVALID").exists())

    def test_foreign_documents_and_permissions_cannot_be_bypassed(self):
        foreign_receipt = self.receipt(wh=self.foreign)
        foreign_count = StockCountModel.objects.create(count_no="FOREIGN", warehouse=self.foreign, status="counted", created_by=self.director)
        transfer = StockTransferModel.objects.create(transfer_no="FOREIGN", source_warehouse=self.wh, destination_warehouse=self.foreign, created_by=self.director)
        for path in [f'receipts/{foreign_receipt.id}/post',f'counts/{foreign_count.id}/approve']:
            self.assertEqual(self.post(path).status_code, 404)
        self.assertEqual(self.post(f'transfers/{transfer.id}/post').status_code,410)
        self.assertEqual(self.post(f'transfers/{transfer.id}/dispatch').status_code,403)
        self.assertEqual(self.client.get('/api/warehouse/transfers', **self.headers()).json()['count'], 1)
        for path in ['receipts','counts']:
            self.assertEqual(self.client.get('/api/warehouse/'+path, **self.headers()).json()['count'], 0)
        self.role.permissions.clear()
        self.assertEqual(self.client.get('/api/warehouse/catalog', **self.headers()).status_code, 403)
        self.assertEqual(self.post(f'receipts/{foreign_receipt.id}/post').status_code, 403)

    def test_receipt_second_line_failure_rolls_back_first_line_and_repeat_is_safe(self):
        receipt = self.receipt()
        second = PurchaseOrderItemModel.objects.create(purchase_order=self.order, sku=self.sku2, ordered_qty=1, unit_price=2)
        bad = PurchaseReceiptItemModel.objects.create(receipt=receipt, po_item=second, qty=2, unit_cost=2)
        self.assertEqual(self.post(f'receipts/{receipt.id}/post').status_code, 400)
        self.assertFalse(StockInventoryModel.objects.exists()); self.assertFalse(StockMovementModel.objects.exists())
        self.line.refresh_from_db(); self.assertEqual(self.line.received_qty, 0)
        bad.qty=1;bad.save(update_fields=['qty'])
        self.assertEqual(self.post(f'receipts/{receipt.id}/post').status_code, 200)
        self.assertEqual(self.post(f'receipts/{receipt.id}/post').status_code, 409)
        self.assertEqual(StockMovementModel.objects.count(), 2)

    def test_stale_count_or_later_line_failure_never_partially_adjusts(self):
        a = StockInventoryModel.objects.create(warehouse=self.wh, sku=self.sku, qty=5)
        b = StockInventoryModel.objects.create(warehouse=self.wh, sku=self.sku2, qty=9)
        response = self.post('counts', {"count_no":"C", "warehouse_id":self.wh.id,"items":[{"sku_id":self.sku.id,"actual_qty":"4","reason":"Count"},{"sku_id":self.sku2.id,"actual_qty":"8","reason":"Count"}]})
        self.assertEqual(response.status_code, 201)
        b.qty=10;b.save(update_fields=['qty'])
        self.assertEqual(self.post(f'counts/{response.json()["id"]}/approve').status_code, 409)
        a.refresh_from_db();self.assertEqual(a.qty, 5);self.assertFalse(StockMovementModel.objects.exists())
        b.qty=9;b.save(update_fields=['qty'])
        self.assertEqual(self.post(f'counts/{response.json()["id"]}/approve').status_code, 200)
        self.assertEqual(self.post(f'counts/{response.json()["id"]}/approve').status_code, 409)
        self.assertEqual(StockMovementModel.objects.count(), 2)

    def test_transfers_preserve_weighted_cost_and_rollback_late_failure(self):
        self.foreign.manager=self.user;self.foreign.save(update_fields=['manager'])
        a = StockInventoryModel.objects.create(warehouse=self.wh, sku=self.sku, qty=5,avg_cost=10)
        dest = StockInventoryModel.objects.create(warehouse=self.foreign, sku=self.sku, qty=5,avg_cost=20)
        transfer=StockTransferModel.objects.create(transfer_no="T",status="approved",source_warehouse=self.wh,destination_warehouse=self.foreign,created_by=self.user)
        StockTransferItemModel.objects.create(transfer=transfer,sku=self.sku,qty=5)
        bad=StockTransferItemModel.objects.create(transfer=transfer,sku=self.sku2,qty=1)
        self.assertEqual(self.post(f'transfers/{transfer.id}/dispatch').status_code, 409)
        a.refresh_from_db();dest.refresh_from_db();self.assertEqual(a.qty,5);self.assertEqual(dest.qty,5)
        bad.delete()
        self.assertEqual(self.post(f'transfers/{transfer.id}/dispatch').status_code, 200)
        self.assertEqual(self.post(f'transfers/{transfer.id}/receive').status_code,200)
        dest.refresh_from_db();self.assertEqual(dest.avg_cost,15)

    def test_audit_failure_rolls_back_receipt_creation(self):
        with patch('backend.presentation.api.warehouse_views.OperationLogModel.objects.create',side_effect=RuntimeError('audit unavailable')):
            response=self.post('receipts',{"receipt_no":"AUDIT","warehouse_id":self.wh.id,"purchase_order_id":self.order.id,"items":[{"po_item_id":self.line.id,"qty":10}]})
        self.assertEqual(response.status_code,500)
        self.assertFalse(PurchaseReceiptModel.objects.filter(receipt_no="AUDIT").exists())

    def test_quantities_are_finite_and_batch_adjustment_is_not_silently_lost(self):
        for value in ['NaN','Infinity','1.0001',True,-1]:
            self.assertEqual(self.post('counts',{"count_no":"BAD","warehouse_id":self.wh.id,"items":[{"sku_id":self.sku.id,"actual_qty":value,"reason":"Check"}]}).status_code,400)
        stock=StockInventoryModel.objects.create(warehouse=self.wh,sku=self.sku,qty=5)
        StockBatchModel.objects.create(inventory=stock,batch_no="B",expiry_date=date.today(),qty=5)
        count=self.post('counts',{"count_no":"BATCH","warehouse_id":self.wh.id,"items":[{"sku_id":self.sku.id,"actual_qty":"4","reason":"Count"}]}).json()
        response = self.post(f'counts/{count["id"]}/approve')
        self.assertEqual(response.status_code,409)
        self.assertEqual(response.json()["code"], "batch_adjustment_required")
        stock.refresh_from_db();self.assertEqual(stock.qty,5)

    def test_overflow_is_rejected_without_po_or_ledger_changes(self):
        stock = StockInventoryModel.objects.create(warehouse=self.wh, sku=self.sku, qty="99999999999.999", avg_cost=1)
        receipt = self.receipt()
        self.assertEqual(self.post(f'receipts/{receipt.id}/post').status_code, 400)
        stock.refresh_from_db(); self.line.refresh_from_db()
        self.assertEqual(stock.qty, Decimal("99999999999.999"))
        self.assertEqual(self.line.received_qty, 0)
        self.assertFalse(StockMovementModel.objects.exists())
        self.foreign.manager=self.user;self.foreign.save(update_fields=['manager'])
        StockInventoryModel.objects.create(warehouse=self.foreign,sku=self.sku,qty=1,avg_cost=1)
        transfer=StockTransferModel.objects.create(transfer_no="OVERFLOW",status="approved",source_warehouse=self.foreign,destination_warehouse=self.wh,created_by=self.user)
        StockTransferItemModel.objects.create(transfer=transfer,sku=self.sku,qty=1)
        self.assertEqual(self.post(f'transfers/{transfer.id}/dispatch').status_code,200)
        self.assertEqual(self.post(f'transfers/{transfer.id}/receive').status_code,400)
        self.assertEqual(StockMovementModel.objects.filter(movement_type='transfer_in').count(),0)

    def test_source_numbers_and_document_lookup_are_scoped(self):
        receipt=self.receipt()
        self.assertEqual(self.post(f'receipts/{receipt.id}/post').status_code,200)
        movement=self.client.get('/api/warehouse/movements',**self.headers()).json()['items'][0]
        self.assertEqual(movement['source_no'],receipt.receipt_no)
        response=self.client.get('/api/warehouse/receipts',{'id':receipt.id},**self.headers()).json()
        self.assertEqual(response['count'],1)
        self.assertEqual(response['items'][0]['id'],receipt.id)
        foreign=self.receipt(number="FOREIGN-SOURCE",wh=self.foreign)
        self.assertEqual(self.client.get('/api/warehouse/receipts',{'id':foreign.id},**self.headers()).json()['count'],0)

    def test_batch_expiry_mismatch_rolls_back_receipt_balance(self):
        stock=StockInventoryModel.objects.create(warehouse=self.wh,sku=self.sku,qty=1,avg_cost=3)
        StockBatchModel.objects.create(inventory=stock,batch_no="EXISTING",expiry_date=date.today(),qty=1)
        receipt=self.receipt()
        line=receipt.items.get();line.batch_no="EXISTING";line.expiry_date=date.today()+timedelta(days=1);line.save()
        self.assertEqual(self.post(f'receipts/{receipt.id}/post').status_code,400)
        stock.refresh_from_db();self.line.refresh_from_db()
        self.assertEqual(stock.qty,1);self.assertEqual(stock.avg_cost,3);self.assertEqual(self.line.received_qty,0)
        self.assertFalse(StockMovementModel.objects.exists())

    def test_legacy_partial_draft_requires_reason_at_posting(self):
        receipt=self.receipt()
        line=receipt.items.get();line.qty=1;line.save(update_fields=['qty'])
        self.assertEqual(self.post(f'receipts/{receipt.id}/post').status_code,400)
        self.assertFalse(StockInventoryModel.objects.exists());self.assertFalse(StockMovementModel.objects.exists())
        line.discrepancy_reason="Partial delivery";line.save(update_fields=['discrepancy_reason'])
        self.assertEqual(self.post(f'receipts/{receipt.id}/post').status_code,200)

    def test_expiry_report_exposes_truncation_and_location(self):
        stock=StockInventoryModel.objects.create(warehouse=self.wh,location=self.location,sku=self.sku,qty=501)
        StockBatchModel.objects.bulk_create([
            StockBatchModel(inventory=stock,batch_no=f"B-{n}",expiry_date=date.today(),qty=1)
            for n in range(501)
        ])
        response=self.client.get('/api/warehouse/alerts/expiry',{'warehouse_id':self.wh.id},**self.headers())
        self.assertEqual(response.status_code,200)
        report=response.json()
        self.assertEqual(report['batches_count'],501)
        self.assertEqual(len(report['batches']),500)
        self.assertTrue(report['truncated'])
        self.assertEqual(report['certificates_count'],0)
        self.assertEqual(report['batches'][0]['location_id'],self.location.id)
        self.assertEqual(report['batches'][0]['location_code'],self.location.code)
