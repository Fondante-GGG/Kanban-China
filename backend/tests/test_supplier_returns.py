"""Supplier return stock, provenance, authorization and finance bridge contracts."""
import json
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest import skipUnless
from django.db import connection, connections

from django.test import Client, TestCase, TransactionTestCase
from django.utils import timezone

from backend.tests import test_stock_writeoffs as writeoff_tests
from backend.infrastructure.persistence.models import (
    SupplierModel, PurchaseOrderModel, PurchaseOrderItemModel, PurchaseReceiptModel,
    PurchaseReceiptItemModel, SupplierReturnModel, SupplierReturnItemModel,
    SupplierReturnFinanceReviewModel, NotificationModel, StockMovementModel,
    StockBatchModel, OperationLogModel, SystemPermissionModel, FinancePayableModel,
)


class SupplierReturnTests(TestCase):
    headers = writeoff_tests.StockWriteoffTests.headers
    photo = writeoff_tests.StockWriteoffTests.photo

    def setUp(self):
        writeoff_tests.StockWriteoffTests.setUp(self)
        for suffix in ('read', 'manage', 'approve', 'post'):
            permission, _ = SystemPermissionModel.objects.get_or_create(
                code='warehouse.return.' + suffix, defaults={'name': suffix})
            self.role.permissions.add(permission)
        self.supplier = SupplierModel.objects.create(name_ru='Supplier', status='approved', created_by=self.director)
        self.order = PurchaseOrderModel.objects.create(po_no='PO-R', supplier=self.supplier,
            order_date=date.today(), status='received', created_by=self.director, currency='CNY')
        self.po_item = PurchaseOrderItemModel.objects.create(purchase_order=self.order, sku=self.sku,
            ordered_qty=10, received_qty=10, unit_price='80')
        self.receipt = PurchaseReceiptModel.objects.create(receipt_no='RC-R', purchase_order=self.order,
            warehouse=self.wh, status='posted', received_by=self.director)
        self.source = PurchaseReceiptItemModel.objects.create(receipt=self.receipt, po_item=self.po_item,
            location=self.loc, qty=10, unit_cost='80')
        self.payable = FinancePayableModel.objects.create(supplier=self.supplier, purchase_order=self.order,
            source_type='test', source_id=1, amount='800', outstanding_amount='800', currency='CNY')

    def post(self, path='', body=None, user=None):
        return self.client.post('/api/warehouse/returns' + path, json.dumps(body or {}),
            content_type='application/json', **self.headers(user))

    def payload(self, number='RT-1', qty=2, reason_type='other'):
        return {'return_no': number, 'receipt_id': self.receipt.id, 'reason_type': reason_type,
            'reason': 'Возврат поставщику', 'items': [{'receipt_item_id': self.source.id, 'qty': qty}]}

    def draft(self, number='RT-1', qty=2, reason_type='other'):
        response = self.post(body=self.payload(number, qty, reason_type))
        self.assertEqual(response.status_code, 201, response.content)
        return SupplierReturnModel.objects.get(id=response.json()['id'])

    def approved(self, number='RT-1', qty=2):
        doc = self.draft(number, qty)
        self.assertEqual(self.post(f'/{doc.id}/submit').status_code, 200)
        self.assertEqual(self.post(f'/{doc.id}/review', {'decision': 'approve'}, self.director).status_code, 200)
        return doc

    def upload(self, doc):
        return self.client.post(f'/api/warehouse/returns/{doc.id}/photos', {'file': self.photo()}, **self.headers())

    def test_post_is_atomic_idempotent_and_preserves_financial_source(self):
        doc = self.approved()
        self.assertEqual(self.post(f'/{doc.id}/post').status_code, 200)
        self.assertEqual(self.post(f'/{doc.id}/post').status_code, 200)
        self.stock.refresh_from_db(); self.po_item.refresh_from_db(); self.payable.refresh_from_db()
        self.assertEqual(self.stock.qty, Decimal('8'))
        self.assertEqual(self.stock.avg_cost, Decimal('40.25'))
        self.assertEqual(self.po_item.received_qty, 10)
        self.assertEqual(self.payable.outstanding_amount, Decimal('800'))
        self.assertEqual(PurchaseReceiptItemModel.objects.get(id=self.source.id).qty, 10)
        self.assertEqual(StockMovementModel.objects.filter(source_type='supplier_return').count(), 1)
        self.assertEqual(SupplierReturnFinanceReviewModel.objects.count(), 1)
        self.assertEqual(NotificationModel.objects.filter(entity_type='supplier_return').count(), 1)
        self.assertEqual(doc.items.get().unit_cost, Decimal('40.25'))
        queue = self.client.get('/api/finance/supplier-returns', **self.headers(self.director)).json()['items'][0]
        self.assertEqual(queue['stock_valuation'], '80.50')
        self.assertEqual(queue['source_currency'], 'CNY')
        self.assertIsNone(queue['valuation_currency'])
        self.assertEqual(queue['valuation_status'], 'currency_unresolved')
        self.assertNotIn('credit_amount', queue)

    def test_cumulative_return_limit_even_with_replenished_stock(self):
        first = self.approved(qty=7)
        second = self.approved('RT-2', qty=7)
        self.assertEqual(self.post(f'/{first.id}/post').status_code, 200)
        self.stock.qty = 20; self.stock.save(update_fields=['qty'])
        response = self.post(f'/{second.id}/post')
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()['code'], 'receipt_limit')
        self.assertEqual(StockMovementModel.objects.count(), 1)

    def test_current_stock_rechecked_after_approval(self):
        doc = self.approved()
        self.stock.qty = 1; self.stock.save(update_fields=['qty'])
        self.assertEqual(self.post(f'/{doc.id}/post').json()['code'], 'insufficient_stock')
        self.assertFalse(SupplierReturnFinanceReviewModel.objects.exists())

    def test_independent_review_and_transitions(self):
        doc = self.draft()
        self.assertEqual(self.post(f'/{doc.id}/post').status_code, 403)
        self.assertEqual(self.post(f'/{doc.id}/submit').status_code, 200)
        self.assertEqual(self.post(f'/{doc.id}/review', {'decision': 'approve'}).status_code, 403)
        self.assertEqual(self.post(f'/{doc.id}/review', {'decision': 'return'}, self.director).status_code, 400)
        self.assertEqual(self.post(f'/{doc.id}/review', {'decision': 'return', 'comment': 'Fix'}, self.director).status_code, 200)
        self.assertEqual(self.post(f'/{doc.id}/submit').status_code, 200)
        self.assertEqual(self.post(f'/{doc.id}/review', {'decision': 'reject', 'comment': 'No'}, self.director).status_code, 200)
        self.assertEqual(self.post(f'/{doc.id}/cancel').status_code, 403)

    def test_scope_and_cost_hiding(self):
        doc = self.approved()
        self.post(f'/{doc.id}/post')
        listing = self.client.get('/api/warehouse/returns', **self.headers()).json()['items'][0]
        self.assertNotIn('unit_cost', listing['items'][0])
        self.assertNotIn('old_data', listing['history'][0])
        self.assertEqual(self.client.get('/api/warehouse/returns', **self.headers(self.foreign)).json()['count'], 0)
        self.assertEqual(self.post(f'/{doc.id}/post', user=self.foreign).status_code, 404)
        self.assertEqual(self.client.get('/api/finance/supplier-returns', **self.headers()).status_code, 403)
        movement = self.client.get('/api/warehouse/movements', **self.headers()).json()['items'][0]
        self.assertEqual(movement['source_no'], doc.return_no)

    def test_damage_requires_photo_and_private_download(self):
        doc = self.draft(reason_type='damage')
        self.assertEqual(self.post(f'/{doc.id}/submit').json()['code'], 'photo_required')
        response = self.upload(doc)
        self.assertEqual(response.status_code, 201, response.content)
        url = response.json()['download_url']
        self.assertEqual(self.client.get(url, **self.headers(self.foreign)).status_code, 404)
        response = self.client.get(url, **self.headers())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Cache-Control'], 'private, no-store')
        response.close()
        self.assertEqual(self.post(f'/{doc.id}/submit').status_code, 200)

    def test_expired_batch_other_reason_cannot_bypass_evidence(self):
        self.source.batch_no = 'expired'; self.source.expiry_date = timezone.localdate()-timedelta(days=1)
        self.source.save(update_fields=['batch_no', 'expiry_date'])
        batch = StockBatchModel.objects.create(inventory=self.stock, batch_no=self.source.batch_no,
            expiry_date=self.source.expiry_date, qty=10)
        doc = self.draft()
        self.assertEqual(self.post(f'/{doc.id}/submit').json()['code'], 'photo_required')
        self.upload(doc)
        self.post(f'/{doc.id}/submit')
        self.post(f'/{doc.id}/review', {'decision': 'approve'}, self.director)
        self.assertEqual(self.post(f'/{doc.id}/post').status_code, 200)
        batch.refresh_from_db(); self.assertEqual(batch.qty, Decimal(8))

    def test_missing_photo_rechecked_at_post(self):
        doc = self.draft(reason_type='damage'); self.upload(doc)
        self.post(f'/{doc.id}/submit'); self.post(f'/{doc.id}/review', {'decision': 'approve'}, self.director)
        from backend.infrastructure.persistence.storage import PrivateMediaStorage
        PrivateMediaStorage().delete(doc.photos.get().file_path)
        self.assertEqual(self.post(f'/{doc.id}/post').json()['code'], 'photo_required')
        self.assertFalse(StockMovementModel.objects.exists())

    def test_audit_failure_rolls_back_all_post_effects(self):
        doc = self.approved()
        with patch('backend.presentation.api.warehouse_return_views.audit', side_effect=RuntimeError('test failure')):
            self.assertEqual(self.post(f'/{doc.id}/post').status_code, 500)
        self.stock.refresh_from_db(); doc.refresh_from_db()
        self.assertEqual(self.stock.qty, Decimal(10)); self.assertEqual(doc.status, 'approved')
        self.assertFalse(SupplierReturnFinanceReviewModel.objects.exists())
        self.assertFalse(NotificationModel.objects.exists())
        self.assertFalse(StockMovementModel.objects.exists())
        self.assertIsNone(doc.items.get().unit_cost)

    def test_notification_failure_rolls_back_stock(self):
        doc = self.approved()
        with patch('backend.presentation.api.warehouse_return_views.NotificationModel.objects.create', side_effect=RuntimeError('test failure')):
            self.assertEqual(self.post(f'/{doc.id}/post').status_code, 500)
        self.stock.refresh_from_db()
        self.assertEqual(self.stock.qty, Decimal(10))
        self.assertFalse(SupplierReturnFinanceReviewModel.objects.exists())

    def test_invalid_duplicate_and_cross_receipt_lines(self):
        for qty in (True, 0, -1, '1.5'):
            self.assertEqual(self.post(body=self.payload(qty=qty)).status_code, 400)
        payload = self.payload(); payload['items'] *= 2
        self.assertEqual(self.post(body=payload).status_code, 400)
        self.receipt.status = 'draft'; self.receipt.save(update_fields=['status'])
        self.assertEqual(self.post(body=self.payload()).status_code, 404)
        self.assertFalse(SupplierReturnModel.objects.exists())

    def test_header_immutable_and_cancel_has_no_stock_effect(self):
        doc = self.draft()
        payload = self.payload('CHANGED')
        response = self.client.patch(f'/api/warehouse/returns/{doc.id}', json.dumps(payload),
            content_type='application/json', **self.headers())
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.post(f'/{doc.id}/cancel').status_code, 200)
        self.assertEqual(self.post(f'/{doc.id}/submit').status_code, 403)
        self.assertFalse(StockMovementModel.objects.exists())

    def test_finance_queue_read_only_and_paginated(self):
        self.assertEqual(self.client.post('/api/finance/supplier-returns', {}, **self.headers(self.director)).status_code, 405)
        self.assertEqual(self.client.get('/api/finance/supplier-returns?limit=101', **self.headers(self.director)).status_code, 400)
        response = self.client.get('/api/warehouse/returns/catalog', **self.headers())
        self.assertEqual(response.status_code, 200)
        receipt = response.json()['receipts'][0]
        self.assertEqual(receipt['items'][0]['returnable_qty'], 10)
        self.assertNotIn('unit_cost', receipt['items'][0])

    def test_finance_photo_link_current_permission_and_missing_file(self):
        doc = self.draft(reason_type='damage'); self.upload(doc)
        self.post(f'/{doc.id}/submit'); self.post(f'/{doc.id}/review', {'decision': 'approve'}, self.director)
        self.post(f'/{doc.id}/post')
        finance_permission, _ = SystemPermissionModel.objects.get_or_create(
            code='finance.payable.read', defaults={'name': 'Finance'})
        self.role.permissions.add(finance_permission)
        queue = self.client.get('/api/finance/supplier-returns', **self.headers(self.foreign)).json()
        url = queue['items'][0]['photos'][0]['download_url']
        response = self.client.get(url, **self.headers(self.foreign))
        self.assertEqual(response.status_code, 200); response.close()
        self.assertEqual(self.client.get(url.replace('/photos/', '/photos/999'), **self.headers(self.foreign)).status_code, 404)
        self.role.permissions.remove(finance_permission)
        self.assertEqual(self.client.get(url, **self.headers(self.foreign)).status_code, 403)
        self.role.permissions.add(finance_permission)
        from backend.infrastructure.persistence.storage import PrivateMediaStorage
        PrivateMediaStorage().delete(doc.photos.get().file_path)
        self.assertEqual(self.client.get(url, **self.headers(self.foreign)).status_code, 404)

    def test_catalog_paging_search_and_exact_origin(self):
        for number in ('RC-A', 'RC-B'):
            PurchaseReceiptModel.objects.create(receipt_no=number, purchase_order=self.order,
                warehouse=self.wh, status='posted', received_by=self.director)
        url = '/api/warehouse/returns/catalog'
        first = self.client.get(url+'?limit=1', **self.headers()).json()
        self.assertEqual(first['receipt_count'], 3); self.assertEqual(len(first['receipts']), 1)
        second = self.client.get(url+'?limit=1&offset=1', **self.headers()).json()
        self.assertNotEqual(first['receipts'][0]['id'], second['receipts'][0]['id'])
        exact = self.client.get(url+f'?receipt_id={self.receipt.id}', **self.headers()).json()
        self.assertEqual(exact['receipt_count'], 1); self.assertEqual(exact['receipts'][0]['id'], self.receipt.id)
        filtered = self.client.get(url+'?q=RC-A', **self.headers()).json()
        self.assertEqual(filtered['receipt_count'], 1)
        self.assertEqual(self.client.get(url+'?limit=101', **self.headers()).status_code, 400)

    def test_evidence_recheck_if_stock_expires_after_approval(self):
        self.source.batch_no = 'today'; self.source.expiry_date = timezone.localdate()
        self.source.save(update_fields=['batch_no', 'expiry_date'])
        StockBatchModel.objects.create(inventory=self.stock, batch_no=self.source.batch_no,
            expiry_date=self.source.expiry_date, qty=10)
        doc = self.approved()
        tomorrow = timezone.localdate()+timedelta(days=1)
        with patch('backend.presentation.api.warehouse_return_views.timezone.localdate', return_value=tomorrow):
            response = self.client.get('/api/warehouse/returns', **self.headers()).json()['items'][0]
            self.assertTrue(response['photos_required'])
            self.assertEqual(self.post(f'/{doc.id}/post').json()['code'], 'photo_required')
        self.assertFalse(StockMovementModel.objects.exists())


# Row-lock claims are tested only against PostgreSQL, never inferred from SQLite.
@skipUnless(connection.vendor == 'postgresql', 'Real row-lock contention requires PostgreSQL')
class SupplierReturnConcurrencyTests(TransactionTestCase):
    setUp = SupplierReturnTests.setUp
    headers = SupplierReturnTests.headers
    photo = SupplierReturnTests.photo
    post = SupplierReturnTests.post
    payload = SupplierReturnTests.payload
    draft = SupplierReturnTests.draft
    approved = SupplierReturnTests.approved

    def concurrent_post(self, ids):
        gate = Barrier(2)
        headers = self.headers()

        def worker(doc_id):
            connections.close_all()
            try:
                gate.wait(timeout=10)
                return Client().post(f'/api/warehouse/returns/{doc_id}/post', '{}',
                    content_type='application/json', **headers).status_code
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(worker, doc_id) for doc_id in ids]
            return [future.result(timeout=20) for future in futures]

    def test_same_document_concurrent_retry_is_idempotent(self):
        doc = self.approved()
        self.assertEqual(self.concurrent_post([doc.id, doc.id]), [200, 200])
        self.stock.refresh_from_db(); self.assertEqual(self.stock.qty, Decimal(8))
        self.assertEqual(StockMovementModel.objects.filter(source_type='supplier_return').count(), 1)
        self.assertEqual(SupplierReturnFinanceReviewModel.objects.count(), 1)
        self.assertEqual(NotificationModel.objects.filter(entity_type='supplier_return').count(), 1)

    def test_competing_documents_cannot_exceed_original_receipt(self):
        first = self.approved(qty=7); second = self.approved('RT-2', qty=7)
        self.stock.qty = 20; self.stock.save(update_fields=['qty'])
        self.assertEqual(sorted(self.concurrent_post([first.id, second.id])), [200, 409])
        self.stock.refresh_from_db(); self.assertEqual(self.stock.qty, Decimal(13))
        self.assertEqual(StockMovementModel.objects.filter(source_type='supplier_return').count(), 1)
        self.assertEqual(SupplierReturnFinanceReviewModel.objects.count(), 1)
