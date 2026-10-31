import json
from datetime import date
from decimal import Decimal
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from unittest import skipUnless
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from PIL import Image, PngImagePlugin
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, TransactionTestCase, override_settings
from django.db import connection, connections

from backend.domain.entities import User
from backend.infrastructure.di.container import container
from backend.infrastructure.persistence.models import (
    DepartmentModel, UserModel, SystemRoleModel, SystemPermissionModel, UserSystemRoleModel,
    WarehouseModel, WarehouseLocationModel, GoodsSKUModel, StockInventoryModel, StockBatchModel,
    StockWriteoffModel, StockWriteoffItemModel, StockWriteoffPhotoModel, StockMovementModel, OperationLogModel,
)


class StockWriteoffTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.enterContext(override_settings(PRIVATE_MEDIA_ROOT=self.tmp.name))
        self.dept = DepartmentModel.objects.create(name='Writeoffs')
        self.sender = UserModel.objects.create_user(email='writeoff.sender@test', password='password123', full_name='Sender', role='employee', department=self.dept)
        self.director = UserModel.objects.create_user(email='writeoff.director@test', password='password123', full_name='Director', role='general_director')
        self.foreign = UserModel.objects.create_user(email='writeoff.foreign@test', password='password123', full_name='Foreign', role='employee', department=self.dept)
        self.wh = WarehouseModel.objects.create(name_ru='Own', manager=self.sender)
        self.other = WarehouseModel.objects.create(name_ru='Foreign')
        self.loc = WarehouseLocationModel.objects.create(warehouse=self.wh, code='A-01')
        self.other_loc = WarehouseLocationModel.objects.create(warehouse=self.other, code='B-01')
        self.sku = GoodsSKUModel.objects.create(sku_code='WO-1', name_ru='Good', status='active', created_by=self.director)
        self.stock = StockInventoryModel.objects.create(warehouse=self.wh, location=self.loc, sku=self.sku, qty=10, avg_cost='40.25')
        self.role = SystemRoleModel.objects.create(code='writeoff_test', name='Writeoffs')
        for suffix in ('read', 'manage', 'approve', 'post'):
            perm, _ = SystemPermissionModel.objects.get_or_create(code='warehouse.writeoff.' + suffix, defaults={'name': suffix})
            self.role.permissions.add(perm)
        inventory_perm, _ = SystemPermissionModel.objects.get_or_create(code='warehouse.inventory.read', defaults={'name': 'Inventory'})
        self.role.permissions.add(inventory_perm)
        UserSystemRoleModel.objects.create(user=self.sender, role=self.role)
        UserSystemRoleModel.objects.create(user=self.foreign, role=self.role)

    def headers(self, user=None):
        user = user or self.sender
        domain = User(id=user.id, email=user.email, password_hash=user.password, full_name=user.full_name, role=user.role, department_id=user.department_id)
        return {'HTTP_AUTHORIZATION': 'Bearer ' + container.jwt_service.generate_token(domain)}

    def post(self, path, body=None, user=None):
        return self.client.post('/api/warehouse/writeoffs' + path, data=json.dumps(body or {}), content_type='application/json', **self.headers(user))

    def payload(self, number='WO-1', rows=None):
        return {'writeoff_no': number, 'warehouse_id': self.wh.id, 'reason': 'Порча',
                'items': rows or [{'sku_id': self.sku.id, 'location_id': self.loc.id, 'qty': '2.500'}]}

    def draft(self, number='WO-1', rows=None):
        response = self.post('', self.payload(number, rows))
        self.assertEqual(response.status_code, 201, response.content)
        return StockWriteoffModel.objects.get(id=response.json()['id'])

    def photo(self, fmt='PNG', name='damage.png', size=(8, 8)):
        output = BytesIO()
        options = {}
        if fmt == 'PNG':
            info = PngImagePlugin.PngInfo(); info.add_text('comment', 'Private metadata')
            options['pnginfo'] = info
        Image.new('RGB', size, 'red').save(output, format=fmt, **options)
        return SimpleUploadedFile(name, output.getvalue(), content_type='image/' + fmt.lower())

    def upload(self, doc, upload=None, user=None):
        return self.client.post(f'/api/warehouse/writeoffs/{doc.id}/photos', {'file': upload or self.photo()}, **self.headers(user))

    def approved(self, number='WO-1', rows=None):
        doc = self.draft(number, rows)
        self.assertEqual(self.upload(doc).status_code, 201)
        self.assertEqual(self.post(f'/{doc.id}/submit').status_code, 200)
        self.assertEqual(self.post(f'/{doc.id}/review', {'decision': 'approve'}, self.director).status_code, 200)
        doc.refresh_from_db()
        return doc

    def test_complete_workflow_only_post_changes_stock_and_repeat_does_not_duplicate(self):
        doc = self.approved()
        self.stock.refresh_from_db(); self.assertEqual(self.stock.qty, 10)
        self.assertEqual(self.post(f'/{doc.id}/post').status_code, 200)
        self.stock.refresh_from_db(); self.assertEqual(self.stock.qty, Decimal('7.500'))
        line = doc.items.get(); self.assertEqual(line.unit_cost, Decimal('40.25'))
        movement = StockMovementModel.objects.get(source_type='stock_writeoff', source_id=doc.id)
        self.assertEqual(movement.qty_delta, Decimal('-2.500')); self.assertEqual(movement.reason, 'Порча')
        self.assertEqual(self.post(f'/{doc.id}/post').status_code, 200)
        self.assertEqual(StockMovementModel.objects.filter(source_type='stock_writeoff', source_id=doc.id).count(), 1)
        self.assertEqual(OperationLogModel.objects.filter(business_type='stock_writeoff', action='warehouse.writeoff_post').count(), 1)
        listing = self.client.get('/api/warehouse/writeoffs', **self.headers()).json()['items'][0]
        self.assertEqual(listing['status'], 'posted'); self.assertEqual(listing['allowed_actions'], [])
        self.assertNotIn('unit_cost', listing['items'][0]); self.assertNotIn('file_path', listing['photos'][0])
        ledger = self.client.get('/api/warehouse/movements', **self.headers()).json()['items'][0]
        self.assertEqual(ledger['source_no'], doc.writeoff_no)
        privileged = self.client.get('/api/warehouse/writeoffs', **self.headers(self.director)).json()['items'][0]
        self.assertEqual(privileged['items'][0]['unit_cost'], '40.25')

    def test_evidence_and_independent_review_are_required_and_immutable_outside_draft(self):
        doc = self.draft()
        self.assertEqual(self.post(f'/{doc.id}/submit').json()['code'], 'photo_required')
        upload = self.upload(doc); self.assertEqual(upload.status_code, 201)
        photo_id = upload.json()['id']
        self.assertEqual(self.post(f'/{doc.id}/submit').status_code, 200)
        self.assertEqual(self.post(f'/{doc.id}/review', {'decision': 'approve'}).status_code, 403)
        self.assertEqual(self.upload(doc, SimpleUploadedFile('bad.png', b'not an image')).status_code, 403)
        self.assertEqual(self.client.delete(f'/api/warehouse/writeoffs/{doc.id}/photos/{photo_id}', **self.headers()).status_code, 403)
        self.assertEqual(self.post(f'/{doc.id}/review', {'decision': 'return'}, self.director).status_code, 400)
        self.assertEqual(self.post(f'/{doc.id}/review', {'decision': 'return', 'comment': 'Уточнить'}, self.director).status_code, 200)
        body = self.payload(); body['reason'] = 'Уточнено'
        response = self.client.patch(f'/api/warehouse/writeoffs/{doc.id}', data=json.dumps(body), content_type='application/json', **self.headers())
        self.assertEqual(response.status_code, 200)
        edit = OperationLogModel.objects.get(action='warehouse.writeoff_edited')
        self.assertEqual(edit.old_data['reason'], 'Порча'); self.assertEqual(edit.new_data['reason'], 'Уточнено')
        delete = self.client.delete(f'/api/warehouse/writeoffs/{doc.id}/photos/{photo_id}', **self.headers())
        self.assertEqual(delete.status_code, 200)
        removed = StockWriteoffPhotoModel.objects.get(id=photo_id)
        self.assertFalse(removed.is_active); self.assertTrue((Path(self.tmp.name)/removed.file_path).exists())
        self.assertEqual(self.post(f'/{doc.id}/submit').status_code, 409)

    def test_scope_revocation_and_private_photo_download_cannot_be_bypassed(self):
        doc = self.draft(); result = self.upload(doc).json()
        self.assertEqual(self.client.get('/api/warehouse/writeoffs', **self.headers(self.foreign)).json()['count'], 0)
        self.assertEqual(self.client.get('/api/warehouse/writeoffs/catalog', **self.headers(self.foreign)).json()['warehouses'], [])
        self.assertEqual(self.post(f'/{doc.id}/submit', user=self.foreign).status_code, 404)
        self.assertEqual(self.client.get(result['download_url'], **self.headers(self.foreign)).status_code, 404)
        self.assertEqual(self.client.get(result['download_url']).status_code, 401)
        download = self.client.get(result['download_url'], **self.headers())
        self.assertEqual(download.status_code, 200); self.assertEqual(download['X-Content-Type-Options'], 'nosniff')
        self.assertEqual(download['Cache-Control'], 'private, no-store')
        decoded = Image.open(BytesIO(b''.join(download.streaming_content)))
        self.assertEqual(decoded.format, 'PNG'); self.assertNotIn('comment', decoded.info)
        self.role.permissions.clear()
        self.assertEqual(self.client.get(result['download_url'], **self.headers()).status_code, 403)
        self.assertEqual(self.post(f'/{doc.id}/submit').status_code, 403)

    def test_image_validation_formats_limits_and_photo_cap(self):
        doc = self.draft()
        for fmt in ('JPEG', 'PNG', 'WEBP'):
            response = self.upload(doc, self.photo(fmt, name='suspicious.exe'))
            self.assertEqual(response.status_code, 201, response.content)
            self.assertFalse(response.json()['file_name'].endswith('.exe'))
        self.assertEqual(self.upload(doc, SimpleUploadedFile('fake.png', b'<svg/>', content_type='image/png')).json()['code'], 'invalid_photo')
        self.assertEqual(self.upload(doc, SimpleUploadedFile('huge.jpg', b'x' * (10 * 1024 * 1024 + 1))).status_code, 400)
        self.assertEqual(self.upload(doc, self.photo(size=(5000, 5000))).status_code, 400)
        self.assertEqual(self.upload(doc).status_code, 201); self.assertEqual(self.upload(doc).status_code, 201)
        self.assertEqual(self.upload(doc).json()['code'], 'photo_limit')

    def test_upload_authorization_precedes_storage_and_audit_failure_cleans_new_file(self):
        doc = self.draft()
        with patch('backend.presentation.api.warehouse_writeoff_views.canonical_photo') as decode:
            self.assertEqual(self.upload(doc, user=self.foreign).status_code, 404)
            decode.assert_not_called()
        with patch('backend.presentation.api.warehouse_writeoff_views.OperationLogModel.objects.create', side_effect=RuntimeError('audit unavailable')):
            self.assertEqual(self.upload(doc).status_code, 500)
        self.assertFalse(StockWriteoffPhotoModel.objects.exists())
        self.assertEqual([path for path in Path(self.tmp.name).rglob('*') if path.is_file()], [])

    def test_batch_lines_fractional_quantities_and_aggregate_validation(self):
        StockBatchModel.objects.create(inventory=self.stock, batch_no='B1', expiry_date=date(2026, 1, 1), qty=4)
        StockBatchModel.objects.create(inventory=self.stock, batch_no='B2', expiry_date=date(2026, 2, 1), qty=3)
        def line(qty, batch='', expiry=None):
            result = {'sku_id': self.sku.id, 'location_id': self.loc.id, 'qty': qty}
            if batch: result.update(batch_no=batch, expiry_date=expiry)
            return result
        self.assertEqual(self.post('', self.payload(rows=[line('4')])).json()['code'], 'batch_required')
        self.assertEqual(self.post('', self.payload(rows=[line('4', 'B1', '2026-01-01'), line('3', 'B2', '2026-02-01'), line('4')])).status_code, 409)
        self.assertEqual(self.post('', self.payload(rows=[line('1'), line('1')])).status_code, 400)
        doc = self.approved(rows=[line('2.250', 'B1', '2026-01-01'), line('1.500', 'B2', '2026-02-01'), line('1.250')])
        self.assertEqual(self.post(f'/{doc.id}/post').status_code, 200)
        self.stock.refresh_from_db(); self.assertEqual(self.stock.qty, 5)
        self.assertEqual(self.stock.batches.get(batch_no='B1').qty, Decimal('1.750'))
        self.assertEqual(self.stock.batches.get(batch_no='B2').qty, Decimal('1.500'))
        self.assertEqual(StockMovementModel.objects.filter(source_type='stock_writeoff', source_id=doc.id).count(), 3)

    def test_missing_evidence_changed_stock_and_audit_failure_never_reduce_stock(self):
        doc = self.draft()
        self.assertEqual(self.upload(doc).status_code, 201); self.assertEqual(self.upload(doc).status_code, 201)
        self.assertEqual(self.post(f'/{doc.id}/submit').status_code, 200)
        self.assertEqual(self.post(f'/{doc.id}/review', {'decision': 'approve'}, self.director).status_code, 200)
        photo = doc.photos.first(); path = Path(self.tmp.name)/photo.file_path
        content = path.read_bytes(); path.unlink()
        self.assertEqual(self.post(f'/{doc.id}/post').json()['code'], 'photo_required')
        self.stock.refresh_from_db(); self.assertEqual(self.stock.qty, 10)
        path.write_bytes(content)
        self.stock.qty = 1; self.stock.save(update_fields=['qty'])
        self.assertEqual(self.post(f'/{doc.id}/post').json()['code'], 'insufficient_stock')
        self.assertFalse(StockMovementModel.objects.exists())
        self.stock.qty = 10; self.stock.save(update_fields=['qty'])
        with patch('backend.presentation.api.warehouse_writeoff_views.OperationLogModel.objects.create', side_effect=RuntimeError('audit unavailable')):
            self.assertEqual(self.post(f'/{doc.id}/post').status_code, 500)
        self.stock.refresh_from_db(); doc.refresh_from_db()
        self.assertEqual(self.stock.qty, 10); self.assertEqual(doc.status, 'approved')
        self.assertIsNone(doc.items.get().unit_cost); self.assertFalse(StockMovementModel.objects.exists())


    def test_strict_validation_foreign_location_and_immutable_header(self):
        for qty in ('NaN', 'Infinity', '-1', '0', '1.0001', True):
            body = self.payload(rows=[{'sku_id': self.sku.id, 'location_id': self.loc.id, 'qty': qty}])
            self.assertEqual(self.post('', body).status_code, 400)
        body = self.payload(); body['items'][0]['location_id'] = self.other_loc.id
        self.assertEqual(self.post('', body).status_code, 400)
        body = self.payload(); body['warehouse_id'] = self.other.id
        self.assertEqual(self.post('', body).status_code, 403)
        doc = self.draft(); body = self.payload('CHANGED')
        self.assertEqual(self.client.patch(f'/api/warehouse/writeoffs/{doc.id}', data=json.dumps(body), content_type='application/json', **self.headers()).status_code, 400)
        self.assertEqual(self.post(f'/{doc.id}/post').status_code, 403)
        self.assertEqual(self.post(f'/{doc.id}/cancel').status_code, 200)
        self.assertEqual(self.post(f'/{doc.id}/submit').status_code, 403)
        self.assertFalse(StockMovementModel.objects.exists())


@skipUnless(connection.vendor == 'postgresql', 'Real row-lock contention requires PostgreSQL')
class WriteoffConcurrencyTests(TransactionTestCase):
    # Reuse fixtures/helpers without inheriting and duplicating the TestCase suite.
    setUp = StockWriteoffTests.setUp
    headers = StockWriteoffTests.headers
    post = StockWriteoffTests.post
    payload = StockWriteoffTests.payload
    draft = StockWriteoffTests.draft
    photo = StockWriteoffTests.photo
    upload = StockWriteoffTests.upload
    approved = StockWriteoffTests.approved

    def test_concurrent_post_creates_one_stock_movement(self):
        doc = self.approved()
        headers = self.headers()
        gate = Barrier(2)

        def worker():
            connections.close_all()
            try:
                gate.wait(timeout=10)
                return Client().post(f'/api/warehouse/writeoffs/{doc.id}/post', data='{}', content_type='application/json', **headers).status_code
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(worker) for _ in range(2)]
            self.assertEqual([future.result(timeout=20) for future in futures], [200, 200])
        self.stock.refresh_from_db()
        self.assertEqual(self.stock.qty, Decimal('7.500'))
        self.assertEqual(StockMovementModel.objects.filter(source_type='stock_writeoff', source_id=doc.id).count(), 1)
        self.assertEqual(OperationLogModel.objects.filter(business_type='stock_writeoff', action='warehouse.writeoff_post').count(), 1)
