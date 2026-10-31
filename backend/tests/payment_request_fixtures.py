"""Approved fixtures only for legacy tests of unrelated period/debt invariants.

Main payment authorization tests exercise the real create/submit/decide API.
"""
from uuid import uuid4
from decimal import Decimal
from backend.infrastructure.persistence.models import FinancePaymentRequestModel, FinancePaymentProofModel, ApprovalRequestModel
from backend.application.payment_requests import financial_snapshot


def approved_payment_fixture(payable, account, actor, amount, payment_date):
    uid=uuid4()
    doc=FinancePaymentRequestModel.objects.create(request_id=uid,request_no="FIX-"+uid.hex,payable=payable,account=account,amount=Decimal(amount),currency=payable.currency,planned_payment_date=payment_date,purpose="Existing invariant fixture",created_by=actor,status="approved")
    approval=ApprovalRequestModel.objects.create(business_type="finance_payment_request",business_id=doc.id,applicant=actor,status="approved",snapshot=financial_snapshot(doc))
    doc.approval=approval;doc.save(update_fields=["approval"])
    proof=FinancePaymentProofModel.objects.create(payment_request=doc,file_path="test-fixture.pdf",file_name="fixture.pdf",content_type="application/pdf",size=20,uploaded_by=actor)
    return {"payment_request_id":doc.id,"proof_id":proof.id}
