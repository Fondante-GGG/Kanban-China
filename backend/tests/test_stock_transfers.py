import json
from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.test import Client, TestCase
from backend.domain.entities import User
from backend.infrastructure.di.container import container
from backend.infrastructure.persistence.models import (
    DepartmentModel, UserModel, SystemPermissionModel, SystemRoleModel, UserSystemRoleModel,
    WarehouseModel, WarehouseLocationModel, GoodsSKUModel, StockInventoryModel,
    StockBatchModel, StockTransferModel, StockMovementModel, OperationLogModel,
)


class StockTransferWorkflowTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.department = DepartmentModel.objects.create(name='Transfers')
        self.sender = self.user('sender')
        self.receiver = self.user('receiver')
        self.outsider = self.user('outsider')
        self.director = self.user('director', 'general_director')
        self.source = WarehouseModel.objects.create(name_ru='Source', manager=self.sender)
        self.destination = WarehouseModel.objects.create(name_ru='Destination', manager=self.receiver)
        self.source_location = WarehouseLocationModel.objects.create(warehouse=self.source, code='A')
        self.destination_location = WarehouseLocationModel.objects.create(warehouse=self.destination, code='B')
        self.sku = GoodsSKUModel.objects.create(sku_code='T1', name_ru='Transfer item', status='active', created_by=self.director)
        self.stock = StockInventoryModel.objects.create(warehouse=self.source, sku=self.sku, location=self.source_location, qty=10, avg_cost=4)
        self.role = SystemRoleModel.objects.create(code='transfer_test', name='Transfer tester')
        for code in ['warehouse.transfer.read', 'warehouse.transfer.manage', 'warehouse.transfer.post', 'warehouse.transfer.receive', 'warehouse.transfer.approve']:
            p,_=SystemPermissionModel.objects.get_or_create(code=code, defaults={'name':code})
            self.role.permissions.add(p)
        for user in (self.sender,self.receiver,self.outsider): UserSystemRoleModel.objects.create(user=user,role=self.role)

    def user(self, name, role='employee'):
        return UserModel.objects.create_user(email=f'{name}@transfer.test',password='password123',full_name=name,role=role,department=self.department)

    def headers(self, user):
        domain=User(id=user.id,email=user.email,password_hash=user.password,full_name=user.full_name,role=user.role,department_id=user.department_id)
        return {'HTTP_AUTHORIZATION':f'Bearer {container.jwt_service.generate_token(domain)}'}

    def post(self, endpoint, body=None, user=None):
        return self.client.post('/api/warehouse/transfers'+endpoint,data=json.dumps(body or {}),content_type='application/json',**self.headers(user or self.sender))

    def payload(self, **changes):
        result={'transfer_no':'TR-1','source_warehouse_id':self.source.id,'destination_warehouse_id':self.destination.id,
                'items':[{'sku_id':self.sku.id,'qty':3,'source_location_id':self.source_location.id,'destination_location_id':self.destination_location.id}]}
        result.update(changes)
        return result

    def create(self, **changes):
        response=self.post('',self.payload(**changes));self.assertEqual(response.status_code,201,response.content)
        return response.json()['id']

    def approve(self, ident):
        self.assertEqual(self.post(f'/{ident}/submit').status_code,200)
        self.assertEqual(self.post(f'/{ident}/review',{'decision':'approve'},self.director).status_code,200)

    def test_full_route_separate_physical_transit_and_idempotent_receive(self):
        ident=self.create(); self.approve(ident)
        self.stock.refresh_from_db();self.assertEqual(self.stock.qty,10)
        self.assertFalse(StockInventoryModel.objects.filter(warehouse=self.destination).exists())
        self.assertEqual(self.post(f'/{ident}/dispatch').status_code,200)
        self.stock.refresh_from_db();self.assertEqual(self.stock.qty,7)
        self.assertFalse(StockInventoryModel.objects.filter(warehouse=self.destination).exists())
        data=self.client.get('/api/warehouse/transfers',**self.headers(self.receiver)).json()['items'][0]
        self.assertEqual(data['in_transit_qty'],'3');self.assertEqual(data['allowed_actions'],['receive'])
        self.assertNotIn('unit_cost',data['items'][0])
        self.assertEqual(self.post(f'/{ident}/receive',user=self.sender).status_code,403)
        self.assertEqual(self.post(f'/{ident}/receive',user=self.receiver).status_code,200)
        self.assertEqual(self.post(f'/{ident}/receive',user=self.receiver).status_code,200)
        self.assertEqual(self.post(f'/{ident}/dispatch').status_code,200)
        dest=StockInventoryModel.objects.get(warehouse=self.destination);self.assertEqual(dest.qty,3);self.assertEqual(dest.avg_cost,4)
        self.assertEqual(StockMovementModel.objects.filter(source_type='stock_transfer',source_id=ident).count(),2)
        self.assertEqual(OperationLogModel.objects.filter(action='warehouse.transfer_receive').count(),1)

    def test_approval_is_independent_and_unapproved_dispatch_cannot_bypass(self):
        ident=self.create()
        self.assertEqual(self.post(f'/{ident}/dispatch').status_code,403)
        self.post(f'/{ident}/submit')
        self.assertEqual(self.post(f'/{ident}/review',{'decision':'approve'}).status_code,403)
        self.assertEqual(self.post(f'/{ident}/post',user=self.director).status_code,410)
        self.assertFalse(StockMovementModel.objects.exists())

    def test_return_edit_resubmit_and_terminal_rejection(self):
        ident=self.create(comment='Document note');self.post(f'/{ident}/submit')
        self.assertEqual(self.post(f'/{ident}/review',{'decision':'return'},self.director).status_code,400)
        self.assertEqual(self.post(f'/{ident}/review',{'decision':'return','comment':'Correct quantities'},self.director).status_code,200)
        review_log = OperationLogModel.objects.get(action='warehouse.transfer_review_return', business_id=ident)
        self.assertEqual(review_log.new_data['comment'], 'Document note')
        self.assertEqual(review_log.new_data['event_comment'], 'Correct quantities')
        body=self.payload(items=[{**self.payload()['items'][0],'qty':2}])
        response=self.client.patch(f'/api/warehouse/transfers/{ident}',data=json.dumps(body),content_type='application/json',**self.headers(self.sender))
        self.assertEqual(response.status_code,200)
        log = OperationLogModel.objects.get(action='warehouse.transfer_edited', business_id=ident)
        self.assertEqual(log.old_data['items'][0]['qty'], 3)
        self.assertEqual(log.new_data['items'][0]['qty'], 2)
        self.assertEqual(log.old_data['items'][0]['source_location_id'], self.source_location.id)
        body['transfer_no']='NEW'
        self.assertEqual(self.client.patch(f'/api/warehouse/transfers/{ident}',data=json.dumps(body),content_type='application/json',**self.headers(self.sender)).status_code,400)
        self.post(f'/{ident}/submit');self.post(f'/{ident}/review',{'decision':'reject','comment':'Rejected'},self.director)
        self.assertEqual(self.post(f'/{ident}/submit').status_code,403)

    def test_cross_warehouse_read_scope_and_catalog_never_expose_other_stock(self):
        ident=self.create()
        self.assertEqual(self.client.get('/api/warehouse/transfers',**self.headers(self.receiver)).json()['count'],1)
        self.assertEqual(self.client.get('/api/warehouse/transfers',**self.headers(self.outsider)).json()['count'],0)
        self.assertEqual(self.post(f'/{ident}/receive',user=self.outsider).status_code,404)
        catalog=self.client.get('/api/warehouse/transfers/catalog',**self.headers(self.receiver)).json()
        self.assertEqual(catalog['stock'],[])
        self.assertEqual([item['id'] for item in catalog['sources']],[self.destination.id])
        self.assertEqual(len(catalog['destinations']),2)
        unassigned = self.client.get('/api/warehouse/transfers/catalog', **self.headers(self.outsider)).json()
        self.assertEqual(unassigned['sources'], [])
        self.assertEqual(unassigned['destinations'], [])
        self.assertEqual(unassigned['stock'], [])
        self.assertEqual(self.post('',self.payload(transfer_no='FOREIGN'),self.receiver).status_code,403)

    def test_batch_moves_with_frozen_cost_and_locations(self):
        StockBatchModel.objects.create(inventory=self.stock,batch_no='BATCH',expiry_date=date(2027,1,1),qty=10)
        line={**self.payload()['items'][0],'batch_no':'BATCH','expiry_date':'2027-01-01'}
        ident=self.create(items=[line]);self.approve(ident)
        self.assertEqual(self.post(f'/{ident}/dispatch').status_code,200)
        self.stock.refresh_from_db();self.stock.avg_cost=99;self.stock.save(update_fields=['avg_cost'])
        self.assertEqual(self.post(f'/{ident}/receive',user=self.receiver).status_code,200)
        dest=StockInventoryModel.objects.get(warehouse=self.destination)
        self.assertEqual(dest.avg_cost,4);self.assertEqual(dest.location_id,self.destination_location.id)
        self.assertEqual(dest.batches.get(batch_no='BATCH').qty,3)
        self.assertEqual(self.stock.batches.get(batch_no='BATCH').qty,7)
        self.assertEqual(self.post('',self.payload(transfer_no='BYPASS')).status_code,409)

    def test_dispatch_late_failure_rolls_back_every_line(self):
        second=GoodsSKUModel.objects.create(sku_code='T2',name_ru='Second',status='active',created_by=self.director)
        b=StockInventoryModel.objects.create(warehouse=self.source,sku=second,qty=5,avg_cost=1)
        ident=self.create(items=[self.payload()['items'][0],{'sku_id':second.id,'qty':5}]);self.approve(ident)
        b.qty=0;b.save(update_fields=['qty'])
        self.assertEqual(self.post(f'/{ident}/dispatch').status_code,409)
        self.stock.refresh_from_db();self.assertEqual(self.stock.qty,10)
        self.assertFalse(StockMovementModel.objects.exists())
        self.assertFalse(StockTransferModel.objects.get(id=ident).items.exclude(unit_cost=None).exists())

    def test_receive_batch_conflict_and_overflow_roll_back_transit(self):
        StockBatchModel.objects.create(inventory=self.stock,batch_no='B',expiry_date=date(2027,1,1),qty=10)
        ident=self.create(items=[{**self.payload()['items'][0],'batch_no':'B','expiry_date':'2027-01-01'}]);self.approve(ident);self.post(f'/{ident}/dispatch')
        dest=StockInventoryModel.objects.create(warehouse=self.destination,location=self.destination_location,sku=self.sku,qty=2,avg_cost=8)
        batch=StockBatchModel.objects.create(inventory=dest,batch_no='B',expiry_date=date(2028,1,1),qty=2)
        self.assertEqual(self.post(f'/{ident}/receive',user=self.receiver).json()['code'],'batch_conflict')
        dest.refresh_from_db();self.assertEqual(dest.qty,2)
        batch.expiry_date=date(2027,1,1);batch.save(update_fields=['expiry_date'])
        dest.qty=Decimal('99999999999.999');dest.save(update_fields=['qty'])
        self.assertEqual(self.post(f'/{ident}/receive',user=self.receiver).status_code,400)
        self.assertEqual(StockTransferModel.objects.get(id=ident).status,'in_transit')
        self.assertEqual(StockMovementModel.objects.count(),1)

    def test_audit_failure_rolls_back_dispatch_and_permission_revocation(self):
        ident=self.create();self.approve(ident)
        with patch('backend.presentation.api.warehouse_transfer_views.OperationLogModel.objects.create',side_effect=RuntimeError('audit failed')):
            self.assertEqual(self.post(f'/{ident}/dispatch').status_code,500)
        self.stock.refresh_from_db();self.assertEqual(self.stock.qty,10)
        self.assertFalse(StockMovementModel.objects.exists())
        self.role.permissions.clear()
        self.assertEqual(self.post(f'/{ident}/dispatch').status_code,403)

    def test_cancel_only_before_dispatch_and_bad_payload_is_atomic(self):
        for value in (True,0,-1,'NaN','1.5'):
            self.assertEqual(self.post('',self.payload(items=[{**self.payload()['items'][0],'qty':value}])).status_code,400)
        self.assertFalse(StockTransferModel.objects.exists())
        ident=self.create();self.approve(ident);self.post(f'/{ident}/dispatch')
        self.assertEqual(self.post(f'/{ident}/cancel',{'comment':'Cancel'}).status_code,403)
        self.assertEqual(StockTransferModel.objects.get(id=ident).status,'in_transit')


from django.test import TransactionTestCase, skipUnlessDBFeature


class ConcurrentStockTransferTests(TransactionTestCase):
    setUp = StockTransferWorkflowTests.setUp
    headers = StockTransferWorkflowTests.headers
    user = StockTransferWorkflowTests.user
    post = StockTransferWorkflowTests.post
    payload = StockTransferWorkflowTests.payload
    create = StockTransferWorkflowTests.create
    approve = StockTransferWorkflowTests.approve

    @skipUnlessDBFeature('has_select_for_update')
    def test_simultaneous_dispatch_and_receive_are_idempotent(self):
        from concurrent.futures import ThreadPoolExecutor
        from threading import Barrier
        from django.db import close_old_connections
        ident = self.create(); self.approve(ident)

        def concurrent(action, user):
            headers = self.headers(user)
            barrier = Barrier(2)
            def request_action():
                close_old_connections()
                try:
                    barrier.wait(timeout=10)
                    return Client().post(f'/api/warehouse/transfers/{ident}/{action}', data='{}', content_type='application/json', **headers).status_code
                finally:
                    close_old_connections()
            with ThreadPoolExecutor(max_workers=2) as pool:
                jobs = [pool.submit(request_action) for _ in range(2)]
                return [job.result(timeout=20) for job in jobs]

        self.assertEqual(concurrent('dispatch', self.sender), [200,200])
        self.stock.refresh_from_db(); self.assertEqual(self.stock.qty,7)
        self.assertEqual(StockMovementModel.objects.count(),1)
        self.assertEqual(concurrent('receive', self.receiver), [200,200])
        self.assertEqual(StockInventoryModel.objects.get(warehouse=self.destination).qty,3)
        self.assertEqual(StockMovementModel.objects.count(),2)
