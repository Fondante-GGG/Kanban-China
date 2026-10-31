"""Real API authorization, immutable approvals, private evidence and money invariants."""
import json
import tempfile
from datetime import date
from decimal import Decimal
from uuid import uuid4
from unittest.mock import patch
from django.test import TestCase, override_settings
from django.core.files.uploadedfile import SimpleUploadedFile
from backend.tests import test_supplier_return_corrections as correction_tests
from backend.infrastructure.persistence.models import (
    UserModel,SystemRoleModel,SystemPermissionModel,UserSystemRoleModel,
    ApprovalFlowModel,ApprovalNodeModel,ApprovalRequestModel,FinancePaymentModel,
    FinancePaymentRequestModel,FinancePaymentProofModel,FinancePeriodModel,
    FinanceAccountModel,OperationLogModel,
)


class PaymentRequestTests(TestCase):
    headers=correction_tests.SupplierReturnCorrectionTests.headers
    def setUp(self):
        correction_tests.SupplierReturnCorrectionTests.setUp(self)
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        setting=override_settings(PRIVATE_MEDIA_ROOT=self.tmp.name);setting.enable();self.addCleanup(setting.disable)
        self.creator=self.director
        self.approver=UserModel.objects.create_user(email="payment.approver@test",password="test",full_name="Approver",role="employee",department=self.dept)
        role=SystemRoleModel.objects.create(code="payment-approver",name="Payment approver")
        for code in ("approval.read","approval.act"):
            p,_=SystemPermissionModel.objects.get_or_create(code=code,defaults={"name":code});role.permissions.add(p)
        UserSystemRoleModel.objects.create(user=self.approver,role=role)
        self.flow=ApprovalFlowModel.objects.create(business_type="finance_payment_request",name="Approved payment route")
        ApprovalNodeModel.objects.create(flow=self.flow,order=1,approver_type="user",user=self.approver)
        self.base="/api/finance/payment-requests"
    def post(self,path,body=None,user=None):
        return self.client.post(path,json.dumps(body or {}),content_type="application/json",**self.headers(user or self.creator))
    def body(self,**changes):
        return {"request_id":str(uuid4()),"request_no":"PAY-"+uuid4().hex,"payable_id":self.payable.id,"account_id":self.account.id,"amount":"100.25","currency":"CNY","planned_payment_date":date.today().isoformat(),"purpose":"Supplier payment",**changes}
    def create(self,body=None):
        response=self.post(self.base,body or self.body());self.assertEqual(response.status_code,201,response.content);return response.json()
    def submit(self,doc):
        response=self.post(f"{self.base}/{doc['id']}/submit");self.assertEqual(response.status_code,202,response.content);return response.json()
    def approve(self,doc,user=None,action="approve"):
        return self.post(f"/api/approvals/{doc['approval_id']}/actions",{"action":action,"comment":"Decision"},user or self.approver)
    def proof(self,doc):
        response=self.client.post(f"{self.base}/{doc['id']}/proofs",{"file":SimpleUploadedFile('proof.pdf',b'%PDF-1.7\nproof\n%%EOF',content_type='application/pdf')},**self.headers(self.creator));self.assertEqual(response.status_code,201,response.content);return response.json()
    def pay(self,doc,proof,**changes):
        return self.post(f"/api/finance/payables/{doc['payable_id']}/payments",{"payment_request_id":doc['id'],"account_id":doc['account_id'],"amount":doc['amount'],"payment_date":doc['planned_payment_date'],"transaction_no":"TX-"+str(doc['id']),"proof_id":proof['id'],**changes})
    def test_real_flow_payment_and_exact_replay_after_closed_period(self):
        doc=self.submit(self.create());self.assertEqual(self.approve(doc).status_code,200)
        proof=self.proof(doc);paid=self.pay(doc,proof);self.assertEqual(paid.status_code,201,paid.content)
        self.payable.refresh_from_db();self.account.refresh_from_db();self.assertEqual(self.payable.outstanding_amount,Decimal('699.75'));self.assertEqual(self.account.balance,Decimal('899.75'))
        FinancePeriodModel.objects.update(is_closed=True)
        self.assertEqual(self.pay(doc,proof).status_code,200);self.assertEqual(self.pay(doc,proof,transaction_no='OTHER').status_code,409)
        self.assertEqual(FinancePaymentModel.objects.count(),1)
        logged=OperationLogModel.objects.get(action='finance.payment_request_paid')
        self.assertEqual(logged.ip_address,'127.0.0.1')
        self.assertEqual(logged.old_data['account_balance'],'1000.00')
        self.assertEqual(logged.new_data['account_balance'],'899.75')
        self.assertEqual(logged.old_data['debt_outstanding_amount'],'800.00')
        self.assertEqual(logged.new_data['debt_outstanding_amount'],'699.75')
    def test_no_approval_no_proof_and_exact_snapshot_required(self):
        self.assertEqual(self.post(f"/api/finance/payables/{self.payable.id}/payments",{"amount":"10"}).json()['code'],'approval_required')
        doc=self.create();proof=self.proof(doc);self.assertEqual(self.pay(doc,proof).status_code,409)
        doc=self.submit(doc);self.assertEqual(self.approve(doc).status_code,200)
        self.assertEqual(self.pay(doc,proof,amount='100.24').json()['code'],'request_conflict')
        self.assertEqual(self.pay(doc,{'id':999}).json()['code'],'proof_required')
        self.assertFalse(FinancePaymentModel.objects.exists())
    def test_no_flow_no_selfapproval_even_director_and_sequential_snapshot(self):
        ApprovalNodeModel.objects.all().delete();ApprovalNodeModel.objects.create(flow=self.flow,order=1,approver_type='user',user=self.creator)
        self.assertEqual(self.post(f"{self.base}/{self.create()['id']}/submit").json()['code'],'approver_unavailable')
        ApprovalNodeModel.objects.all().delete();ApprovalNodeModel.objects.create(flow=self.flow,order=1,approver_type='user',user=self.approver)
        other=UserModel.objects.create_user(email='other.approver@test',password='test',full_name='Other',role='general_director')
        ApprovalNodeModel.objects.create(flow=self.flow,order=2,approver_type='user',user=other)
        doc=self.submit(self.create());ApprovalNodeModel.objects.filter(order=2).delete()
        self.assertEqual(self.approve(doc,self.creator).status_code,403)
        self.assertEqual(self.approve(doc).json()['status'],'pending')
        self.assertEqual(self.approve(doc,other).json()['status'],'approved')
        self.flow.is_active=False;self.flow.save()
        self.assertEqual(self.post(f"{self.base}/{self.create()['id']}/submit").json()['code'],'flow_unconfigured')
    def test_return_edit_new_snapshot_old_approver_cannot_download_future_proof(self):
        doc=self.create();old=self.proof(doc);doc=self.submit(doc)
        self.assertEqual(self.client.get(old['download_url'],**self.headers(self.approver)).status_code,200)
        self.assertEqual(self.approve(doc,action='return').status_code,200)
        new=self.proof(doc)
        self.assertEqual(self.client.get(new['download_url'],**self.headers(self.approver)).status_code,403)
        changed={k:v for k,v in self.body(amount='50.00').items() if k not in ('request_id','request_no')}
        response=self.client.patch(f"{self.base}/{doc['id']}",json.dumps(changed),content_type='application/json',**self.headers(self.creator));self.assertEqual(response.status_code,200,response.content)
        fresh=self.submit(doc);self.assertNotEqual(fresh['approval_id'],doc['approval_id'])
        self.assertEqual(self.approve(doc).status_code,403)
        self.assertEqual(self.approve(fresh).status_code,200)
    def test_create_replay_original_payload_survives_draft_edit(self):
        body=self.body();doc=self.create(body)
        self.assertEqual(self.post(self.base,body).status_code,200)
        patchbody={k:v for k,v in body.items() if k not in ('request_id','request_no')};patchbody['amount']='20.00'
        self.client.patch(f"{self.base}/{doc['id']}",json.dumps(patchbody),content_type='application/json',**self.headers(self.creator))
        self.assertEqual(self.post(self.base,body).status_code,200)
        self.assertEqual(self.post(self.base,{**body,'amount':'30.00'}).status_code,409)
    def test_closed_period_and_current_funds_rechecked_without_reservation(self):
        doc=self.submit(self.create());self.assertEqual(self.approve(doc).status_code,200);proof=self.proof(doc)
        self.account.balance=Decimal('1');self.account.save();self.assertEqual(self.pay(doc,proof).json()['code'],'insufficient_balance')
        self.account.balance=1000;self.account.save();self.payable.outstanding_amount=Decimal('1');self.payable.save();self.assertEqual(self.pay(doc,proof).json()['code'],'insufficient_outstanding')
        self.payable.outstanding_amount=800;self.payable.save();FinancePeriodModel.objects.update(is_closed=True)
        self.assertEqual(self.pay(doc,proof).json()['code'],'period_closed')
        self.assertFalse(FinancePaymentModel.objects.exists())
    def test_cancel_pending_withdraws_approval_and_proof_immutable_after_paid(self):
        doc=self.submit(self.create());self.assertEqual(self.post(f"{self.base}/{doc['id']}/cancel",{'comment':'Withdraw'}).status_code,200)
        self.assertEqual(ApprovalRequestModel.objects.get(id=doc['approval_id']).status,'withdrawn');self.assertEqual(self.approve(doc).status_code,403)
        doc=self.submit(self.create());self.approve(doc);proof=self.proof(doc);self.pay(doc,proof)
        self.assertEqual(self.client.delete(f"{self.base}/{doc['id']}/proofs/{proof['id']}",**self.headers(self.creator)).status_code,409)
    def test_strict_money_permissions_catalog_and_protected_evidence(self):
        for amount in ('NaN','Infinity','1e2','1.001','-1',1.2,True):self.assertEqual(self.post(self.base,self.body(amount=amount)).status_code,400)
        self.assertEqual(self.client.get(self.base,**self.headers(self.approver)).status_code,403)
        doc=self.create();bad=self.client.post(f"{self.base}/{doc['id']}/proofs",{'file':SimpleUploadedFile('bad.pdf',b'bad',content_type='application/pdf')},**self.headers(self.creator));self.assertEqual(bad.status_code,400)
        proof=self.proof(doc);self.assertEqual(self.client.get(proof['download_url'],**self.headers(self.approver)).status_code,403)
        catalog=self.client.get(self.base+'/catalog',**self.headers(self.creator)).json();self.assertNotIn('balance',catalog['accounts'][0]);self.assertTrue(catalog['flow_configured'])
    def test_other_finance_manager_cannot_edit_submit_or_cancel_anothers_request(self):
        other=UserModel.objects.create_user(email='other.finance@test',password='test',full_name='Other finance',role='general_director')
        doc=self.create()
        body={k:v for k,v in self.body().items() if k not in ('request_id','request_no')}
        response=self.client.patch(f"{self.base}/{doc['id']}",json.dumps(body),content_type='application/json',**self.headers(other))
        self.assertEqual(response.status_code,403)
        self.assertEqual(self.post(f"{self.base}/{doc['id']}/submit",user=other).status_code,403)
        self.assertEqual(self.post(f"{self.base}/{doc['id']}/cancel",{'comment':'No'},other).status_code,403)
        detail=self.client.get(f"{self.base}/{doc['id']}",**self.headers(other)).json()
        self.assertNotIn('edit',detail['allowed_actions']);self.assertNotIn('submit',detail['allowed_actions']);self.assertNotIn('cancel',detail['allowed_actions'])

    def test_payment_audit_failure_rolls_back_all_money(self):
        doc=self.submit(self.create());self.approve(doc);proof=self.proof(doc)
        with patch('backend.application.payment_requests.audit',side_effect=RuntimeError('audit unavailable')):
            self.assertEqual(self.pay(doc,proof).status_code,500)
        self.payable.refresh_from_db();self.account.refresh_from_db();self.assertEqual(self.payable.outstanding_amount,Decimal('800'));self.assertEqual(self.account.balance,Decimal('1000'));self.assertFalse(FinancePaymentModel.objects.exists())


from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest import skipUnless
from django.db import connection, connections
from django.test import TransactionTestCase, Client
from backend.tests.payment_request_fixtures import approved_payment_fixture


@skipUnless(connection.vendor=='postgresql','Real row-lock contention requires PostgreSQL')
class PaymentRequestConcurrencyTests(TransactionTestCase):
    headers=PaymentRequestTests.headers
    def setUp(self):
        correction_tests.SupplierReturnCorrectionTests.setUp(self)
        self.actor=self.director
    def run_parallel(self,bodies):
        barrier=Barrier(2)
        def run(body):
            connections.close_all()
            try:
                barrier.wait(timeout=10)
                return Client().post(f'/api/finance/payables/{self.payable.id}/payments',json.dumps(body),content_type='application/json',**self.headers(self.actor)).status_code
            finally:connections.close_all()
        with patch('backend.application.payment_requests.PrivateMediaStorage.exists',return_value=True),ThreadPoolExecutor(max_workers=2) as pool:return list(pool.map(run,bodies))
    def payment_body(self,amount):
        fixture=approved_payment_fixture(self.payable,self.account,self.actor,amount,date.today())
        return {**fixture,'amount':amount,'account_id':self.account.id,'payment_date':date.today().isoformat(),'transaction_no':'CONCURRENT-'+str(fixture['payment_request_id'])}
    def test_two_approved_requests_cannot_overspend_debt(self):
        responses=self.run_parallel([self.payment_body('500.00'),self.payment_body('500.00')]);self.assertCountEqual(responses,[201,409]);self.payable.refresh_from_db();self.account.refresh_from_db();self.assertEqual(self.payable.outstanding_amount,Decimal('300.00'));self.assertEqual(self.account.balance,Decimal('500.00'));self.assertEqual(FinancePaymentModel.objects.count(),1)
    def test_duplicate_request_executes_once(self):
        body=self.payment_body('100.00');responses=self.run_parallel([body,body]);self.assertCountEqual(responses,[201,200]);self.payable.refresh_from_db();self.assertEqual(self.payable.outstanding_amount,Decimal('700.00'));self.assertEqual(FinancePaymentModel.objects.count(),1)
