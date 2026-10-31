import json
from datetime import date, timedelta
from django.test import TestCase, Client
from backend.infrastructure.di.container import container
from backend.infrastructure.persistence.models import (DepartmentModel, UserModel, SystemPermissionModel, SystemRoleModel, UserSystemRoleModel, SupplierModel, GoodsSKUModel, SupplierQuoteModel, GoodsPriceHistoryModel, PurchaseOrderModel, PurchaseOrderItemModel, PurchaseReceiptModel, PurchaseReceiptItemModel, WarehouseModel, StockInventoryModel, StockMovementModel, StockBatchModel, StockTransferModel, StockTransferItemModel, GoodsCertificateModel)
from backend.domain.entities import User


class ProcurementWarehouseTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.department = DepartmentModel.objects.create(name="Purchasing")
        self.director = UserModel.objects.create_user(email="director.procurement@test.local", password="password123", full_name="Director", role="general_director", department=self.department)
        domain = User(id=self.director.id, email=self.director.email, password_hash=self.director.password, full_name=self.director.full_name, role=self.director.role, department_id=self.department.id)
        self.headers = {"HTTP_AUTHORIZATION": f"Bearer {container.jwt_service.generate_token(domain)}"}

    def complete_transfer_fixture(self, ident):
        # These legacy integration scenarios begin from an approved fixture.
        # Independent approval itself is covered by test_stock_transfers.
        StockTransferModel.objects.filter(id=ident).update(status="approved")
        self.assertEqual(self.client.post(f"/api/warehouse/transfers/{ident}/dispatch", **self.headers).status_code, 200)
        self.assertEqual(self.client.post(f"/api/warehouse/transfers/{ident}/receive", **self.headers).status_code, 200)

    def test_supplier_sku_order_and_receipt_posting_updates_ledger(self):
        supplier_response = self.client.post("/api/procurement/suppliers", data=json.dumps({"name_ru": "Поставщик", "currency": "KGS"}), content_type="application/json", **self.headers)
        self.assertEqual(supplier_response.status_code, 201)
        supplier = SupplierModel.objects.get(id=supplier_response.json()["id"]); supplier.status = "active"; supplier.save()
        sku_response = self.client.post("/api/procurement/skus", data=json.dumps({"sku_code": "SKU-001", "name_ru": "Товар"}), content_type="application/json", **self.headers)
        self.assertEqual(sku_response.status_code, 201)
        sku = GoodsSKUModel.objects.get(id=sku_response.json()["id"]); sku.status = "active"; sku.save()
        order_response = self.client.post("/api/procurement/purchase-orders", data=json.dumps({"po_no": "PO-001", "supplier_id": supplier.id, "department_id": self.department.id, "order_date": date.today().isoformat(), "items": [{"sku_id": sku.id, "ordered_qty": 5, "unit_price": "10.00"}]}), content_type="application/json", **self.headers)
        self.assertEqual(order_response.status_code, 201)
        order = PurchaseOrderModel.objects.get(id=order_response.json()["id"])
        order.status = "approved"; order.save(update_fields=["status"])
        warehouse = WarehouseModel.objects.create(name_ru="Main")
        receipt = PurchaseReceiptModel.objects.create(receipt_no="REC-001", purchase_order=order, warehouse=warehouse, received_by=self.director)
        PurchaseReceiptItemModel.objects.create(receipt=receipt, po_item=PurchaseOrderItemModel.objects.get(purchase_order=order), qty=5, unit_cost="10.00", batch_no="B-001", expiry_date=date.today() + timedelta(days=30))
        response = self.client.post(f"/api/warehouse/receipts/{receipt.id}/post", **self.headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(StockInventoryModel.objects.get(warehouse=warehouse, sku=sku).qty, 5)
        self.assertEqual(StockMovementModel.objects.filter(source_id=receipt.id, movement_type="receipt").count(), 1)
        self.assertEqual(StockBatchModel.objects.get(batch_no="B-001").qty, 5)
        self.assertEqual(PurchaseOrderModel.objects.get(id=order.id).status, "received")

    def test_receipt_cannot_exceed_order_quantity(self):
        supplier = SupplierModel.objects.create(name_ru="Supplier", status="active", created_by=self.director)
        sku = GoodsSKUModel.objects.create(sku_code="SKU-002", name_ru="Good", status="active", created_by=self.director)
        order = PurchaseOrderModel.objects.create(po_no="PO-002", supplier=supplier, order_date=date.today(), status="approved", created_by=self.director)
        item = PurchaseOrderItemModel.objects.create(purchase_order=order, sku=sku, ordered_qty=1, unit_price="1")
        warehouse = WarehouseModel.objects.create(name_ru="Warehouse")
        receipt = PurchaseReceiptModel.objects.create(receipt_no="REC-002", purchase_order=order, warehouse=warehouse, received_by=self.director)
        PurchaseReceiptItemModel.objects.create(receipt=receipt, po_item=item, qty=2, unit_cost="1")
        self.assertEqual(self.client.post(f"/api/warehouse/receipts/{receipt.id}/post", **self.headers).status_code, 400)
        self.assertEqual(StockMovementModel.objects.count(), 0)

    def test_supplier_activation_requires_approval(self):
        created = self.client.post("/api/procurement/suppliers", data=json.dumps({"name_ru": "Approval supplier"}), content_type="application/json", **self.headers).json()
        submitted = self.client.post(f"/api/procurement/suppliers/{created['id']}/submit", **self.headers)
        self.assertEqual(submitted.status_code, 202)
        self.assertEqual(self.client.post(f"/api/approvals/{submitted.json()['id']}/actions", data=json.dumps({"action": "approve"}), content_type="application/json", **self.headers).status_code, 200)
        self.assertEqual(SupplierModel.objects.get(id=created["id"]).status, "active")

    def test_sku_activation_requires_approval(self):
        created = self.client.post("/api/procurement/skus", data=json.dumps({"sku_code": "SKU-APP", "name_ru": "Approval SKU"}), content_type="application/json", **self.headers).json()
        submitted = self.client.post(f"/api/procurement/skus/{created['id']}/submit", **self.headers)
        self.assertEqual(submitted.status_code, 202)
        self.assertEqual(self.client.post(f"/api/approvals/{submitted.json()['id']}/actions", data=json.dumps({"action": "approve"}), content_type="application/json", **self.headers).status_code, 200)
        self.assertEqual(GoodsSKUModel.objects.get(id=created["id"]).status, "active")

    def test_rejected_catalog_record_returns_to_editable_draft(self):
        created = self.client.post("/api/procurement/suppliers", data=json.dumps({"name_ru": "Rejected supplier"}), content_type="application/json", **self.headers).json()
        submitted = self.client.post(f"/api/procurement/suppliers/{created['id']}/submit", **self.headers)
        response = self.client.post(f"/api/approvals/{submitted.json()['id']}/actions", data=json.dumps({"action": "reject", "comment": "Missing tax details"}), content_type="application/json", **self.headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(SupplierModel.objects.get(id=created["id"]).status, "draft")

    def test_transfer_moves_balance_through_ledger(self):
        sku = GoodsSKUModel.objects.create(sku_code="SKU-TRANSFER", name_ru="Transfer", status="active", created_by=self.director)
        source = WarehouseModel.objects.create(name_ru="Source"); destination = WarehouseModel.objects.create(name_ru="Destination")
        StockInventoryModel.objects.create(warehouse=source, sku=sku, qty=5, avg_cost="4.00")
        transfer = StockTransferModel.objects.create(transfer_no="TR-001", source_warehouse=source, destination_warehouse=destination, created_by=self.director)
        StockTransferItemModel.objects.create(transfer=transfer, sku=sku, qty=3)
        self.assertEqual(self.client.post(f"/api/warehouse/transfers/{transfer.id}/post", **self.headers).status_code, 410)
        self.complete_transfer_fixture(transfer.id)
        self.assertEqual(StockInventoryModel.objects.get(warehouse=source, sku=sku).qty, 2)
        self.assertEqual(StockInventoryModel.objects.get(warehouse=destination, sku=sku).qty, 3)
        self.assertEqual(StockMovementModel.objects.filter(source_id=transfer.id).count(), 2)

    def test_warehouse_documents_can_be_created_and_posted_via_api(self):
        supplier = SupplierModel.objects.create(name_ru="Supplier API", status="active", created_by=self.director)
        sku = GoodsSKUModel.objects.create(sku_code="SKU-API", name_ru="API item", status="active", created_by=self.director)
        order = PurchaseOrderModel.objects.create(po_no="PO-API", supplier=supplier, order_date=date.today(), status="approved", created_by=self.director)
        line = PurchaseOrderItemModel.objects.create(purchase_order=order, sku=sku, ordered_qty=4, unit_price="5")
        source = WarehouseModel.objects.create(name_ru="Source API")
        destination = WarehouseModel.objects.create(name_ru="Destination API")
        receipt = self.client.post("/api/warehouse/receipts", data=json.dumps({"receipt_no": "REC-API", "purchase_order_id": order.id, "warehouse_id": source.id, "items": [{"po_item_id": line.id, "qty": 4, "unit_cost": "5"}]}), content_type="application/json", **self.headers)
        self.assertEqual(receipt.status_code, 201)
        self.assertEqual(self.client.post(f"/api/warehouse/receipts/{receipt.json()['id']}/post", **self.headers).status_code, 200)
        transfer = self.client.post("/api/warehouse/transfers", data=json.dumps({"transfer_no": "TR-API", "source_warehouse_id": source.id, "destination_warehouse_id": destination.id, "items": [{"sku_id": sku.id, "qty": 2}]}), content_type="application/json", **self.headers)
        self.assertEqual(transfer.status_code, 201)
        self.complete_transfer_fixture(transfer.json()['id'])
        count = self.client.post("/api/warehouse/counts", data=json.dumps({"count_no": "CNT-API", "warehouse_id": destination.id, "items": [{"sku_id": sku.id, "actual_qty": "1", "reason": "Damage"}]}), content_type="application/json", **self.headers)
        self.assertEqual(count.status_code, 201)
        self.assertEqual(self.client.post(f"/api/warehouse/counts/{count.json()['id']}/approve", **self.headers).status_code, 200)
        self.assertEqual(StockInventoryModel.objects.get(warehouse=destination, sku=sku).qty, 1)

    def test_expiry_alerts_include_batches_and_certificates(self):
        sku = GoodsSKUModel.objects.create(sku_code="SKU-EXP", name_ru="Expiring", status="active", created_by=self.director)
        warehouse = WarehouseModel.objects.create(name_ru="Expiry warehouse")
        inventory = StockInventoryModel.objects.create(warehouse=warehouse, sku=sku, qty=2, avg_cost="1")
        StockBatchModel.objects.create(inventory=inventory, batch_no="EXP-1", expiry_date=date.today() + timedelta(days=5), qty=2)
        GoodsCertificateModel.objects.create(sku=sku, number="CERT-1", file_path="certificate.pdf", expires_at=date.today() + timedelta(days=3), created_by=self.director)
        response = self.client.get("/api/warehouse/alerts/expiry?days=10", **self.headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["batches"][0]["batch_no"], "EXP-1")
        self.assertEqual(response.json()["certificates"][0]["number"], "CERT-1")

    def test_sku_certificate_can_be_registered_and_listed(self):
        sku = GoodsSKUModel.objects.create(sku_code="SKU-CERT", name_ru="Certified", status="active", created_by=self.director)
        created = self.client.post(f"/api/procurement/skus/{sku.id}/certificates", data=json.dumps({"number": "KR-2026-1", "file_path": "certificates/kr-2026-1.pdf", "expires_at": (date.today() + timedelta(days=365)).isoformat()}), content_type="application/json", **self.headers)
        self.assertEqual(created.status_code, 201)
        listed = self.client.get(f"/api/procurement/skus/{sku.id}/certificates", **self.headers)
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(listed.json()["items"][0]["number"], "KR-2026-1")

    def test_existing_supplier_price_requires_approval_and_keeps_history(self):
        supplier = SupplierModel.objects.create(name_ru="Priced supplier", status="active", created_by=self.director)
        sku = GoodsSKUModel.objects.create(sku_code="SKU-PRICE", name_ru="Priced SKU", status="active", created_by=self.director)
        quote = SupplierQuoteModel.objects.create(supplier=supplier, sku=sku, price="10", currency="KGS")
        requested = self.client.post("/api/procurement/quotes", data=json.dumps({"supplier_id": supplier.id, "sku_id": sku.id, "price": "12", "currency": "KGS"}), content_type="application/json", **self.headers)
        self.assertEqual(requested.status_code, 202)
        self.assertEqual(SupplierQuoteModel.objects.get(id=quote.id).price, 10)
        self.assertEqual(self.client.post(f"/api/approvals/{requested.json()['id']}/actions", data=json.dumps({"action": "approve"}), content_type="application/json", **self.headers).status_code, 200)
        self.assertEqual(SupplierQuoteModel.objects.get(id=quote.id).price, 12)
        self.assertEqual(GoodsPriceHistoryModel.objects.filter(sku=sku, new_price="12").count(), 1)

    def test_inventory_reader_cannot_see_average_cost_without_separate_permission(self):
        sku = GoodsSKUModel.objects.create(sku_code="SKU-HIDDEN-COST", name_ru="Hidden cost", status="active", created_by=self.director)
        warehouse = WarehouseModel.objects.create(name_ru="Cost warehouse")
        StockInventoryModel.objects.create(warehouse=warehouse, sku=sku, qty=2, avg_cost="99.50")
        user = UserModel.objects.create_user(email="inventory.reader@test", password="password123", full_name="Reader", role="employee", department=self.department)
        warehouse.manager = user; warehouse.save(update_fields=["manager"])
        permission, _ = SystemPermissionModel.objects.get_or_create(code="warehouse.inventory.read", defaults={"name":"Read inventory"})
        role = SystemRoleModel.objects.create(code="inventory_reader_test", name="Inventory reader")
        role.permissions.add(permission); UserSystemRoleModel.objects.create(user=user, role=role)
        domain = User(id=user.id, email=user.email, password_hash=user.password, full_name=user.full_name, role=user.role, department_id=user.department_id)
        response = self.client.get("/api/warehouse/inventory", HTTP_AUTHORIZATION=f"Bearer {container.jwt_service.generate_token(domain)}")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("avg_cost", response.json()["items"][0])

    def test_purchase_order_requires_approval_before_receipt(self):
        supplier = SupplierModel.objects.create(name_ru="Order supplier", status="active", created_by=self.director)
        sku = GoodsSKUModel.objects.create(sku_code="SKU-ORDER-APP", name_ru="Order SKU", status="active", created_by=self.director)
        created = self.client.post("/api/procurement/purchase-orders", data=json.dumps({"po_no":"PO-APPROVAL", "supplier_id":supplier.id, "order_date":date.today().isoformat(), "items":[{"sku_id":sku.id,"ordered_qty":2,"unit_price":"10"}]}), content_type="application/json", **self.headers)
        self.assertEqual(created.status_code, 201)
        submitted = self.client.post(f"/api/procurement/purchase-orders/{created.json()['id']}/submit", **self.headers)
        self.assertEqual(submitted.status_code, 202)
        self.assertEqual(PurchaseOrderModel.objects.get(id=created.json()["id"]).status, "pending_approval")
        self.assertEqual(self.client.post(f"/api/approvals/{submitted.json()['id']}/actions", data=json.dumps({"action":"approve"}), content_type="application/json", **self.headers).status_code, 200)
        self.assertEqual(PurchaseOrderModel.objects.get(id=created.json()["id"]).status, "approved")
