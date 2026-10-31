"""Phase-one HR, approval and independent system-RBAC API.

Board authorization intentionally remains in the Kanban use cases; permissions
defined here never grant access to a board.
"""
import json
import hashlib
import secrets
from datetime import timedelta
from django.conf import settings
from django.core.mail import send_mail
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.http import JsonResponse
from django.utils import timezone
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.views.decorators.csrf import csrf_exempt
from backend.infrastructure.persistence.models import (
    ApprovalActionModel, ApprovalRequestModel, BoardMemberModel, BoardModel, DepartmentModel,
    ApprovalFlowModel, ApprovalNodeModel, DocumentVersionModel, EmailOutboxModel, EmployeeModel,
    OnboardingInvitationModel, OperationLogModel, SystemPermissionModel,
    SystemRoleModel, UserModel, UserSystemRoleModel,
)
from backend.presentation.api.utils import parse_json_body
from backend.presentation.middlewares import login_required_domain


ALL_PERMISSIONS = ["hr.employee.read", "hr.employee.create", "hr.employee.edit", "hr.employee.submit", "hr.employee.approve", "hr.employee.terminate", "hr.employee.onboarding", "rbac.manage", "approval.read", "approval.act", "audit.read", "attendance.timesheet.confirm", "procurement.supplier.read", "procurement.supplier.manage", "procurement.sku.read", "procurement.sku.manage", "procurement.quote.manage", "procurement.order.read", "procurement.order.manage", "warehouse.receipt.read", "warehouse.receipt.manage", "warehouse.receipt.post", "warehouse.inventory.read", "warehouse.cost.read", "warehouse.count.read", "warehouse.count.manage", "warehouse.count.approve", "warehouse.transfer.read", "warehouse.transfer.manage", "warehouse.transfer.post", "warehouse.transfer.approve", "warehouse.transfer.receive", "warehouse.writeoff.read", "warehouse.writeoff.manage", "warehouse.writeoff.approve", "warehouse.writeoff.post", "finance.account.manage", "finance.payable.read", "finance.payable.manage", "finance.payment.manage", "finance.salary.read", "finance.salary.manage", "kpi.read", "kpi.manage", "admin.asset.read", "admin.asset.manage", "admin.request.manage", "admin.notice.read", "admin.notice.manage", "admin.license.read", "admin.license.manage"]


def _permissions(user_id):
    if UserModel.objects.filter(id=user_id, role="general_director").exists():
        return set(ALL_PERMISSIONS)
    return set(SystemPermissionModel.objects.filter(roles__user_links__user_id=user_id, roles__is_active=True).values_list("code", flat=True).distinct())


def _is_capable_approver(user):
    return bool(user and user.is_active and {"approval.read", "approval.act"}.issubset(_permissions(user.id)))


def _role_is_capable_approver(role_id):
    codes = set(SystemPermissionModel.objects.filter(roles__id=role_id).values_list("code", flat=True))
    return {"approval.read", "approval.act"}.issubset(codes)


def _require(request, code):
    if code not in _permissions(request.user_entity.id):
        return JsonResponse({"error": "Permission denied"}, status=403)
    return None


def _employee_scope(user):
    """Explicit HR data scopes: self; legacy manager's department; HR role all."""
    if user.role == "general_director": return "all"
    if user.role == "manager": return "department"
    if SystemRoleModel.objects.filter(user_links__user_id=user.id, code="hr_manager", is_active=True).exists(): return "all"
    return "self"


def _scoped_employees(user, qs):
    scope = _employee_scope(user)
    if scope == "all": return qs
    if scope == "department": return qs.filter(department_id=user.department_id)
    return qs.filter(user_id=user.id)


def _employee_data(employee):
    return {"id": employee.id, "employee_no": employee.employee_no, "email": employee.email, "full_name_ru": employee.full_name_ru, "full_name_zh": employee.full_name_zh, "full_name_ky": employee.full_name_ky, "department_id": employee.department_id, "position": employee.position, "phone": employee.phone, "status": employee.status, "user_id": employee.user_id, "kanban_role": employee.kanban_role, "board_id": employee.board_id, "created_at": employee.created_at.isoformat()}

@login_required_domain
def employee_documents_view(request, employee_id):
    denied = _require(request, "hr.employee.read")
    if denied: return denied
    employee = _scoped_employees(request.user_entity, EmployeeModel.objects.all()).filter(id=employee_id).first()
    if not employee: return JsonResponse({"error": "Employee not found"}, status=404)
    from backend.infrastructure.persistence.models import EmployeeFileModel, EmployeeChangeModel
    return JsonResponse({"files": [{"id": x.id, "file_name": x.file_name, "file_type": x.file_type, "expires_at": x.expires_at.isoformat() if x.expires_at else None, "version_no": x.version_no} for x in EmployeeFileModel.objects.filter(employee=employee)], "changes": [{"id": x.id, "change_type": x.change_type, "created_at": x.created_at.isoformat()} for x in EmployeeChangeModel.objects.filter(employee=employee)]})


def _version(employee, actor, reason, extra_payload=None):
    payload = _employee_data(employee)
    if extra_payload:
        payload.update(extra_payload)
    current = DocumentVersionModel.objects.filter(document_type="employee", document_id=employee.id).count()
    DocumentVersionModel.objects.create(document_type="employee", document_id=employee.id, version_no=current + 1, payload=payload, changed_by_id=actor.id, reason=reason)
    OperationLogModel.objects.create(actor_id=actor.id, action=reason, business_type="employee", business_id=employee.id, new_data=payload)


def _has_board_in_department(board_id, department_id):
    return not board_id or BoardModel.objects.filter(id=board_id, department_id=department_id, is_archived=False).exists()


def _resolve_node_assignee(node, employee):
    """Resolve the next approver from a configured node without granting board access."""
    if node.approver_type == "user":
        return node.user if _is_capable_approver(node.user) else None
    if node.approver_type == "role" and node.role_id:
        candidates = UserModel.objects.filter(
            system_role_links__role_id=node.role_id, is_active=True,
        ).order_by("id")
        return next((candidate for candidate in candidates if _is_capable_approver(candidate)), None)
    if node.approver_type == "department_leader":
        candidates = UserModel.objects.filter(
            department_id=employee.department_id, role="manager", is_active=True,
        ).order_by("id")
        return next((candidate for candidate in candidates if _is_capable_approver(candidate)), None)
    return None


def _approval_flow_and_assignee(employee, business_type):
    flow = ApprovalFlowModel.objects.filter(business_type=business_type, is_active=True).prefetch_related("nodes__role", "nodes__user").first()
    if flow:
        node = flow.nodes.order_by("order").first()
        if node:
            assignee = _resolve_node_assignee(node, employee)
            if assignee:
                return flow, node, assignee
    # Transitional safe fallback for installations not yet configured.  It is
    # deliberately restricted to an existing director rather than a broad role.
    return flow, None, UserModel.objects.filter(role="general_director", is_active=True).order_by("id").first()


def _can_view_approval(user, approval):
    return user.role == "general_director" or approval.assigned_to_id == user.id or approval.applicant_id == user.id


def _serialize_approval(approval):
    return {
        "id": approval.id, "business_type": approval.business_type,
        "business_id": approval.business_id, "status": approval.status,
        "applicant_id": approval.applicant_id, "assigned_to_id": approval.assigned_to_id,
        "flow_id": approval.flow_id, "current_node": approval.current_node,
        "created_at": approval.created_at.isoformat(),
    }


def _flow_data(flow):
    return {
        "id": flow.id, "business_type": flow.business_type, "name": flow.name,
        "is_active": flow.is_active,
        "nodes": [{"id": node.id, "order": node.order, "approver_type": node.approver_type,
                   "user_id": node.user_id, "role_id": node.role_id}
                  for node in flow.nodes.order_by("order")],
    }


@csrf_exempt
@login_required_domain
def approval_flows_view(request):
    """Administrator API for the first approval-flow editor vertical slice."""
    denied = _require(request, "rbac.manage")
    if denied: return denied
    if request.method == "GET":
        flows = ApprovalFlowModel.objects.prefetch_related("nodes").order_by("business_type")
        return JsonResponse({"items": [_flow_data(flow) for flow in flows]})
    if request.method != "POST": return JsonResponse({"error": "Method not allowed"}, status=405)
    data = parse_json_body(request)
    business_type, name, nodes = str(data.get("business_type", "")).strip(), str(data.get("name", "")).strip(), data.get("nodes", [])
    if not business_type or not name or not isinstance(nodes, list) or not nodes:
        return JsonResponse({"error": "business_type, name and at least one node are required"}, status=400)
    allowed = {"user", "role", "department_leader"}
    try:
        with transaction.atomic():
            flow = ApprovalFlowModel.objects.create(business_type=business_type, name=name)
            seen = set()
            for raw in nodes:
                order, approver_type = int(raw.get("order", 0)), raw.get("approver_type")
                if order < 1 or order in seen or approver_type not in allowed:
                    raise ValueError
                seen.add(order)
                user_id, role_id = raw.get("user_id") or None, raw.get("role_id") or None
                if approver_type == "user":
                    candidate = UserModel.objects.filter(id=user_id, is_active=True).first()
                    if not _is_capable_approver(candidate): raise ValueError
                if approver_type == "role":
                    if not SystemRoleModel.objects.filter(id=role_id, is_active=True).exists() or not _role_is_capable_approver(role_id): raise ValueError
                if approver_type == "department_leader":
                    # Department leaders must have a dedicated role with both
                    # approval permissions; resolve-time filtering enforces it
                    # for the actual department employee.
                    if not SystemRoleModel.objects.filter(code="department_leader", is_active=True).filter(permissions__code="approval.read").exists() or not _role_is_capable_approver(SystemRoleModel.objects.get(code="department_leader").id): raise ValueError
                    user_id = role_id = None
                ApprovalNodeModel.objects.create(flow=flow, order=order, approver_type=approver_type, user_id=user_id, role_id=role_id)
    except (ValueError, TypeError):
        return JsonResponse({"error": "Invalid approval node configuration"}, status=422)
    except Exception:
        return JsonResponse({"error": "Approval flow already exists"}, status=409)
    return JsonResponse(_flow_data(flow), status=201)


@csrf_exempt
@login_required_domain
def employees_view(request):
    if request.method == "GET":
        denied = _require(request, "hr.employee.read")
        if denied: return denied
        qs = _scoped_employees(request.user_entity, EmployeeModel.objects.filter(is_deleted=False).select_related("department"))
        if request.GET.get("department_id"): qs = qs.filter(department_id=request.GET["department_id"])
        if request.GET.get("status"): qs = qs.filter(status=request.GET["status"])
        if request.GET.get("q"): qs = qs.filter(full_name_ru__icontains=request.GET["q"])
        page, size = max(int(request.GET.get("page", 1)), 1), min(max(int(request.GET.get("page_size", 25)), 1), 100)
        total = qs.count(); items = qs[(page-1)*size:page*size]
        return JsonResponse({"items": [_employee_data(item) for item in items], "page": page, "page_size": size, "total": total})
    if request.method != "POST": return JsonResponse({"error": "Method not allowed"}, status=405)
    denied = _require(request, "hr.employee.create")
    if denied: return denied
    data = parse_json_body(request)
    needed = ["employee_no", "email", "full_name_ru", "department_id"]
    if any(not str(data.get(k, "")).strip() for k in needed): return JsonResponse({"error": "employee_no, email, full_name_ru and department_id are required"}, status=400)
    if not DepartmentModel.objects.filter(id=data["department_id"]).exists(): return JsonResponse({"error": "Department not found"}, status=422)
    if UserModel.objects.filter(email__iexact=data["email"]).exists(): return JsonResponse({"error": "Email already belongs to an account"}, status=409)
    try:
        with transaction.atomic():
            board_id = data.get("board_id") or None
            if not _has_board_in_department(board_id, data["department_id"]): return JsonResponse({"error": "Board must belong to employee department"}, status=422)
            employee = EmployeeModel.objects.create(employee_no=data["employee_no"].strip(), email=data["email"].strip().lower(), full_name_ru=data["full_name_ru"].strip(), full_name_zh=data.get("full_name_zh", ""), full_name_ky=data.get("full_name_ky", ""), department_id=data["department_id"], position=data.get("position", ""), phone=data.get("phone", ""), kanban_role=data.get("kanban_role", "employee"), board_id=board_id)
            _version(employee, request.user_entity, "employee.created")
        return JsonResponse(_employee_data(employee), status=201)
    except Exception as exc:
        return JsonResponse({"error": "Employee number or email already exists"}, status=409)


@csrf_exempt
@login_required_domain
def employee_detail_view(request, employee_id):
    employee = EmployeeModel.objects.filter(id=employee_id, is_deleted=False).first()
    if not employee: return JsonResponse({"error": "Employee not found"}, status=404)
    if request.method == "GET":
        if not _scoped_employees(request.user_entity, EmployeeModel.objects.filter(id=employee.id)).exists(): return JsonResponse({"error": "Permission denied"}, status=403)
        return JsonResponse(_employee_data(employee))
    if request.method != "PATCH": return JsonResponse({"error": "Method not allowed"}, status=405)
    denied = _require(request, "hr.employee.edit")
    if denied: return denied
    if employee.status not in ("draft", "returned"): return JsonResponse({"error": "Only draft employees can be changed"}, status=409)
    data = parse_json_body(request)
    if _employee_scope(request.user_entity) != "all" and not _scoped_employees(request.user_entity, EmployeeModel.objects.filter(id=employee.id)).exists(): return JsonResponse({"error": "Permission denied"}, status=403)
    for field in ("full_name_ru", "full_name_zh", "full_name_ky", "position", "phone", "kanban_role", "board_id"):
        if field in data: setattr(employee, field, data[field] or (None if field == "board_id" else ""))
    if "department_id" in data:
        if not DepartmentModel.objects.filter(id=data["department_id"]).exists(): return JsonResponse({"error": "Department not found"}, status=422)
        employee.department_id = data["department_id"]
    if not _has_board_in_department(employee.board_id, employee.department_id): return JsonResponse({"error": "Board must belong to employee department"}, status=422)
    with transaction.atomic():
        employee.save(); _version(employee, request.user_entity, "employee.updated")
    return JsonResponse(_employee_data(employee))


@csrf_exempt
@login_required_domain
def employee_submit_view(request, employee_id, termination=False):
    if request.method != "POST": return JsonResponse({"error": "Method not allowed"}, status=405)
    denied = _require(request, "hr.employee.terminate" if termination else "hr.employee.submit")
    if denied: return denied
    employee = EmployeeModel.objects.filter(id=employee_id, is_deleted=False).first()
    if not employee: return JsonResponse({"error": "Employee not found"}, status=404)
    expected = "active" if termination else "draft"
    if employee.status != expected: return JsonResponse({"error": "Invalid employee lifecycle state"}, status=409)
    data = parse_json_body(request)
    termination_reason = str(data.get("reason", "")).strip() if termination else ""
    if termination and not termination_reason:
        return JsonResponse({"error": "Termination reason is required"}, status=400)
    if termination:
        from backend.infrastructure.persistence.models import AdminAssetLogModel
        issued = set(AdminAssetLogModel.objects.filter(employee_id=employee.id, operation="issued").values_list("asset_id", flat=True))
        returned = set(AdminAssetLogModel.objects.filter(employee_id=employee.id, operation="returned").values_list("asset_id", flat=True))
        if issued - returned:
            return JsonResponse({"error": "Employee has unreturned assets"}, status=409)
    with transaction.atomic():
        if not termination: employee.status = "pending_approval"; employee.save(update_fields=["status", "updated_at"])
        business_type = "employee_termination" if termination else "employee_hire"
        flow, node, approver = _approval_flow_and_assignee(employee, business_type)
        if not approver: return JsonResponse({"error": "No approval authority configured"}, status=409)
        snapshot = _employee_data(employee)
        if termination:
            snapshot["termination_reason"] = termination_reason
        approval = ApprovalRequestModel.objects.create(
            business_type=business_type, business_id=employee.id,
            applicant_id=request.user_entity.id, assigned_to=approver, flow=flow,
            current_node=node.order if node else 1, snapshot=snapshot,
        )
        ApprovalActionModel.objects.create(approval=approval, actor_id=request.user_entity.id, action="submit")
        _version(
            employee, request.user_entity,
            "employee.termination_submitted" if termination else "employee.submitted",
            {"termination_reason": termination_reason} if termination else None,
        )
    return JsonResponse({"id": approval.id, "status": approval.status}, status=202)


@csrf_exempt
@login_required_domain
def approval_action_view(request, approval_id):
    if request.method != "POST": return JsonResponse({"error": "Method not allowed"}, status=405)
    denied = _require(request, "approval.act")
    if denied: return denied
    data = parse_json_body(request); action = data.get("action")
    if action not in ("approve", "reject", "return"): return JsonResponse({"error": "Invalid action"}, status=400)
    if action in ("reject", "return") and not str(data.get("comment", "")).strip(): return JsonResponse({"error": "Comment is required"}, status=400)
    with transaction.atomic():
        approval = ApprovalRequestModel.objects.select_for_update().filter(id=approval_id).first()
        if not approval: return JsonResponse({"error": "Approval not found"}, status=404)
        if approval.status != "pending": return JsonResponse({"error": "Approval is already closed"}, status=409)
        if request.user_entity.role != "general_director" and approval.assigned_to_id != request.user_entity.id:
            return JsonResponse({"error": "Approval is not assigned to current user"}, status=403)
        employee = EmployeeModel.objects.select_for_update().filter(id=approval.business_id).first() if approval.business_type.startswith("employee_") else None
        if action == "approve":
            next_node = None
            next_assignee = None
            if approval.flow_id and employee:
                next_node = approval.flow.nodes.filter(order__gt=approval.current_node).order_by("order").first()
                if next_node:
                    next_assignee = _resolve_node_assignee(next_node, employee)
                    if not next_assignee:
                        return JsonResponse({"error": "Next approval node has no active approver"}, status=409)
            if next_node:
                approval.current_node = next_node.order
                approval.assigned_to = next_assignee
                approval.save(update_fields=["current_node", "assigned_to"])
                ApprovalActionModel.objects.create(approval=approval, actor_id=request.user_entity.id, action="approve", comment=data.get("comment", ""))
                return JsonResponse({"id": approval.id, "status": approval.status, "assigned_to_id": approval.assigned_to_id, "current_node": approval.current_node})
            approval.status = "approved"
            if approval.business_type == "employee_hire":
                if UserModel.objects.filter(email__iexact=employee.email).exists(): return JsonResponse({"error": "Employee email already belongs to an account"}, status=409)
                user = UserModel.objects.create_user(email=employee.email, full_name=employee.full_name_ru, department_id=employee.department_id, phone=employee.phone, role=employee.kanban_role, is_active=True)
                employee.user = user; employee.status = "active"; employee.hired_at = timezone.localdate(); employee.save()
                if employee.board_id: BoardMemberModel.objects.get_or_create(board_id=employee.board_id, user=user, defaults={"role": employee.kanban_role})
            elif approval.business_type == "employee_termination":
                employee.status = "terminated"; employee.terminated_at = timezone.localdate(); employee.user.is_active = False; employee.user.save(update_fields=["is_active"]); employee.save()
            elif approval.business_type == "supplier":
                from backend.infrastructure.persistence.models import SupplierModel
                SupplierModel.objects.filter(id=approval.business_id, status="pending_approval").update(status="active")
            elif approval.business_type == "sku":
                from backend.infrastructure.persistence.models import GoodsSKUModel
                GoodsSKUModel.objects.filter(id=approval.business_id, status="pending_approval").update(status="active")
            elif approval.business_type == "supplier_quote_price":
                from decimal import Decimal
                from django.utils import timezone as django_timezone
                from backend.infrastructure.persistence.models import SupplierQuoteModel, GoodsPriceHistoryModel
                quote = SupplierQuoteModel.objects.select_for_update().filter(id=approval.business_id).first()
                if not quote: return JsonResponse({"error": "Supplier quote no longer exists"}, status=409)
                if str(quote.price) != str(approval.snapshot.get("old_price")):
                    return JsonResponse({"error": "Supplier quote changed; submit a new price request"}, status=409)
                new_price = Decimal(str(approval.snapshot["new_price"]))
                quote.price = new_price; quote.moq = int(approval.snapshot["moq"]); quote.delivery_days = int(approval.snapshot["delivery_days"]); quote.save(update_fields=["price", "moq", "delivery_days"])
                GoodsPriceHistoryModel.objects.create(sku_id=quote.sku_id, price_type="supplier_quote", currency=quote.currency, old_price=Decimal(str(approval.snapshot["old_price"])), new_price=new_price, effective_at=django_timezone.now(), changed_by_id=request.user_entity.id, approval_id=approval.id)
            elif approval.business_type == "purchase_order":
                from backend.infrastructure.persistence.models import PurchaseOrderModel
                updated = PurchaseOrderModel.objects.filter(id=approval.business_id, status="pending_approval").update(status="approved")
                if not updated: return JsonResponse({"error": "Purchase order is not awaiting approval"}, status=409)
        elif action == "return":
            approval.status = "returned"
            if approval.business_type == "employee_hire": employee.status = "draft"; employee.save(update_fields=["status", "updated_at"])
            elif approval.business_type == "supplier":
                from backend.infrastructure.persistence.models import SupplierModel
                SupplierModel.objects.filter(id=approval.business_id).update(status="draft")
            elif approval.business_type == "sku":
                from backend.infrastructure.persistence.models import GoodsSKUModel
                GoodsSKUModel.objects.filter(id=approval.business_id).update(status="draft")
            elif approval.business_type == "purchase_order":
                from backend.infrastructure.persistence.models import PurchaseOrderModel
                PurchaseOrderModel.objects.filter(id=approval.business_id).update(status="draft")
        else:
            approval.status = "rejected"
            # Rejected catalog records return to an editable draft state, but
            # the immutable approval decision remains available in its history.
            if approval.business_type == "supplier":
                from backend.infrastructure.persistence.models import SupplierModel
                SupplierModel.objects.filter(id=approval.business_id).update(status="draft")
            elif approval.business_type == "sku":
                from backend.infrastructure.persistence.models import GoodsSKUModel
                GoodsSKUModel.objects.filter(id=approval.business_id).update(status="draft")
            elif approval.business_type == "purchase_order":
                from backend.infrastructure.persistence.models import PurchaseOrderModel
                PurchaseOrderModel.objects.filter(id=approval.business_id).update(status="draft")
        approval.decided_by_id = request.user_entity.id; approval.decided_at = timezone.now(); approval.save()
        ApprovalActionModel.objects.create(approval=approval, actor_id=request.user_entity.id, action=action, comment=data.get("comment", ""))
        if approval.business_type in ("supplier", "sku", "purchase_order"):
            OperationLogModel.objects.create(actor_id=request.user_entity.id, action="approval." + action, business_type=approval.business_type, business_id=approval.business_id, new_data={"approval_id": approval.id, "status": approval.status})
        if employee:
            _version(employee, request.user_entity, "approval." + action)
    return JsonResponse({"id": approval.id, "status": approval.status, "employee": _employee_data(employee) if employee else None})


@login_required_domain
def approvals_inbox_view(request):
    if request.method != "GET": return JsonResponse({"error": "Method not allowed"}, status=405)
    denied = _require(request, "approval.read")
    if denied: return denied
    scope = request.GET.get("scope", "assigned")
    if scope not in ("assigned", "submitted", "completed"):
        return JsonResponse({"error": "Invalid scope"}, status=400)
    qs = ApprovalRequestModel.objects.select_related("applicant", "assigned_to", "flow").order_by("-created_at")
    if scope == "submitted":
        qs = qs.filter(applicant_id=request.user_entity.id)
    elif scope == "completed":
        qs = qs.exclude(status="pending")
        if request.user_entity.role != "general_director":
            from django.db.models import Q
            qs = qs.filter(Q(assigned_to_id=request.user_entity.id) | Q(applicant_id=request.user_entity.id))
    elif request.user_entity.role != "general_director":
        qs = qs.filter(assigned_to_id=request.user_entity.id)
    if request.GET.get("status"): qs = qs.filter(status=request.GET["status"])
    page, size = max(int(request.GET.get("page", 1)), 1), min(max(int(request.GET.get("page_size", 25)), 1), 100)
    total = qs.count(); qs = qs[(page-1)*size:page*size]
    return JsonResponse({"items": [_serialize_approval(a) for a in qs], "scope": scope, "page": page, "page_size": size, "total": total})


@login_required_domain
def approval_detail_view(request, approval_id):
    if request.method != "GET": return JsonResponse({"error": "Method not allowed"}, status=405)
    denied = _require(request, "approval.read")
    if denied: return denied
    approval = ApprovalRequestModel.objects.select_related("applicant", "assigned_to").filter(id=approval_id).first()
    if not approval: return JsonResponse({"error": "Approval not found"}, status=404)
    if not _can_view_approval(request.user_entity, approval): return JsonResponse({"error": "Permission denied"}, status=403)
    actions = [{"action": a.action, "comment": a.comment, "actor_id": a.actor_id, "created_at": a.created_at.isoformat()} for a in approval.actions.select_related("actor").all()]
    versions = [{"version_no": v.version_no, "reason": v.reason, "created_at": v.created_at.isoformat()} for v in DocumentVersionModel.objects.filter(document_type="employee", document_id=approval.business_id)]
    result = _serialize_approval(approval)
    result.update({"snapshot": approval.snapshot, "actions": actions, "versions": versions})
    return JsonResponse(result)


@login_required_domain
def audit_view(request):
    if request.method != "GET": return JsonResponse({"error": "Method not allowed"}, status=405)
    denied = _require(request, "audit.read")
    if denied: return denied
    qs = OperationLogModel.objects.all()
    if request.GET.get("business_type"): qs = qs.filter(business_type=request.GET["business_type"])
    if request.GET.get("business_id"): qs = qs.filter(business_id=request.GET["business_id"])
    return JsonResponse({"items": [{"id": item.id, "action": item.action, "business_type": item.business_type, "business_id": item.business_id, "actor_id": item.actor_id, "created_at": item.created_at.isoformat()} for item in qs[:200]]})


@csrf_exempt
@login_required_domain
def rbac_roles_view(request):
    denied = _require(request, "rbac.manage")
    if denied: return denied
    if request.method == "GET": return JsonResponse({"items": [{"id": r.id, "code": r.code, "name": r.name, "description": r.description, "permission_ids": list(r.permissions.values_list("id", flat=True)), "permissions": list(r.permissions.values_list("code", flat=True))} for r in SystemRoleModel.objects.prefetch_related("permissions").all()]})
    if request.method != "POST": return JsonResponse({"error": "Method not allowed"}, status=405)
    data = parse_json_body(request)
    role = SystemRoleModel.objects.create(code=data.get("code", "").strip(), name=data.get("name", "").strip(), description=data.get("description", ""))
    return JsonResponse({"id": role.id, "code": role.code, "name": role.name}, status=201)


@login_required_domain
def rbac_permissions_view(request):
    """Return the complete seeded permission catalogue for RBAC editors.

    Role responses intentionally contain only currently assigned permissions;
    this endpoint keeps a clean installation administrable without granting any
    additional business data access.
    """
    if request.method != "GET":
        return JsonResponse({"error": "Method not allowed"}, status=405)
    denied = _require(request, "rbac.manage")
    if denied:
        return denied
    permissions = SystemPermissionModel.objects.order_by("code")
    return JsonResponse({"items": [
        {"id": permission.id, "code": permission.code, "name": permission.name,
         "description": permission.description}
        for permission in permissions
    ]})


@login_required_domain
def rbac_users_view(request):
    """Safe account catalogue for independent RBAC administration.

    This deliberately does not reuse ``/users``: that endpoint administers
    legacy Kanban users and is intentionally limited by the board-admin policy.
    A system RBAC administrator needs only the minimal account identity and
    current system-role assignment required to manage module access.
    """
    if request.method != "GET":
        return JsonResponse({"error": "Method not allowed"}, status=405)
    denied = _require(request, "rbac.manage")
    if denied:
        return denied
    query = request.GET.get("q", "").strip()
    users = UserModel.objects.prefetch_related("system_role_links__role").order_by("full_name", "id")
    if query:
        from django.db.models import Q
        users = users.filter(Q(full_name__icontains=query) | Q(email__icontains=query))
    page = max(int(request.GET.get("page", 1)), 1)
    size = min(max(int(request.GET.get("page_size", 50)), 1), 100)
    total = users.count()
    users = users[(page - 1) * size: page * size]
    return JsonResponse({
        "items": [{
            "id": user.id,
            "full_name": user.full_name,
            "email": user.email,
            "is_active": user.is_active,
            "system_role_ids": [link.role_id for link in user.system_role_links.all()],
            "system_roles": [
                {"id": link.role_id, "code": link.role.code, "name": link.role.name}
                for link in user.system_role_links.all()
            ],
        } for user in users],
        "page": page,
        "page_size": size,
        "total": total,
    })


@csrf_exempt
@login_required_domain
def rbac_role_permissions_view(request, role_id):
    denied = _require(request, "rbac.manage")
    if denied: return denied
    if request.method != "PUT": return JsonResponse({"error": "Method not allowed"}, status=405)
    role = SystemRoleModel.objects.filter(id=role_id).first()
    if not role: return JsonResponse({"error": "Role not found"}, status=404)
    data = parse_json_body(request); ids = data.get("permission_ids")
    codes = data.get("permissions", [])
    perms = list(SystemPermissionModel.objects.filter(id__in=ids)) if ids is not None else list(SystemPermissionModel.objects.filter(code__in=codes))
    expected = ids if ids is not None else codes
    if len(perms) != len(set(expected)): return JsonResponse({"error": "Unknown permission"}, status=422)
    role.permissions.set(perms)
    return JsonResponse({"id": role.id, "permission_ids": list(role.permissions.values_list("id", flat=True)), "permissions": list(role.permissions.values_list("code", flat=True))})


@csrf_exempt
@login_required_domain
def user_system_roles_view(request, user_id):
    denied = _require(request, "rbac.manage")
    if denied: return denied
    if request.method != "PUT": return JsonResponse({"error": "Method not allowed"}, status=405)
    user = UserModel.objects.filter(id=user_id).first()
    if not user: return JsonResponse({"error": "User not found"}, status=404)
    ids = parse_json_body(request).get("role_ids", [])
    roles = list(SystemRoleModel.objects.filter(id__in=ids, is_active=True))
    if len(roles) != len(set(ids)): return JsonResponse({"error": "Unknown role"}, status=422)
    UserSystemRoleModel.objects.filter(user=user).delete()
    UserSystemRoleModel.objects.bulk_create([UserSystemRoleModel(user=user, role=role) for role in roles])
    return JsonResponse({"user_id": user.id, "role_ids": [r.id for r in roles]})


@csrf_exempt
@login_required_domain
def onboarding_link_view(request, employee_id):
    if request.method != "POST": return JsonResponse({"error": "Method not allowed"}, status=405)
    denied = _require(request, "hr.employee.onboarding")
    if denied: return denied
    employee = EmployeeModel.objects.filter(id=employee_id, status="active", user__isnull=False).select_related("user").first()
    if not employee: return JsonResponse({"error": "Active employee not found"}, status=404)
    outbox = EmailOutboxModel.objects.filter(to_email=employee.user.email, status__in=("waiting_configuration", "pending", "failed")).order_by("-created_at").first()
    last_at = outbox.created_at if outbox else None
    if last_at and last_at > timezone.now() - timedelta(minutes=5):
        return JsonResponse({"error": "Invitation was recently requested"}, status=429)
    # Do not mint an un-deliverable invitation.  A durable outbox request can be
    # retried once mail is configured, at which point a fresh secret is minted.
    if not getattr(settings, "EMAIL_HOST", ""):
        # Idempotent pending request: do not grow the outbox while delivery is
        # unavailable and, importantly, do not mint an undeliverable secret.
        if not outbox or outbox.status != "waiting_configuration":
            EmailOutboxModel.objects.create(
                to_email=employee.user.email, subject="Set your Yrys password",
                body="onboarding invitation awaiting mail configuration", status="waiting_configuration",
            )
        OperationLogModel.objects.create(actor_id=request.user_entity.id, action="employee.onboarding_queued", business_type="employee", business_id=employee.id)
        return JsonResponse({"delivery": "waiting_mail_configuration"}, status=202)
    raw_token = secrets.token_urlsafe(32)
    invitation = OnboardingInvitationModel.objects.create(user=employee.user, token_hash=hashlib.sha256(raw_token.encode()).hexdigest(), expires_at=timezone.now() + timedelta(hours=24), created_by_id=request.user_entity.id)
    outbox = EmailOutboxModel.objects.create(to_email=employee.user.email, subject="Set your Yrys password", body="onboarding invitation", invitation=invitation, status="pending")
    link = f"{getattr(settings, 'FRONTEND_URL', 'http://localhost:3001')}/onboarding?token={raw_token}"
    delivery = "pending"
    try:
        send_mail("Set your Yrys password", f"Use this one-time link within 24 hours: {link}", getattr(settings, "DEFAULT_FROM_EMAIL", None), [employee.user.email], fail_silently=False)
        now = timezone.now(); invitation.sent_at = now; invitation.save(update_fields=["sent_at"])
        outbox.status = "sent"; outbox.sent_at = now; outbox.attempts = 1; outbox.save(update_fields=["status", "sent_at", "attempts"]); delivery = "sent"
    except Exception:
        # The raw token is intentionally discarded.  A later resend creates a
        # new invitation; no secret remains in the database or API response.
        invitation.expires_at = timezone.now(); invitation.save(update_fields=["expires_at"])
        outbox.status = "failed"; outbox.attempts = 1; outbox.last_error = "delivery_failed"; outbox.save(update_fields=["status", "attempts", "last_error"])
    OperationLogModel.objects.create(actor_id=request.user_entity.id, action="employee.onboarding_invited", business_type="employee", business_id=employee.id)
    return JsonResponse({"delivery": delivery, "expires_at": invitation.expires_at.isoformat()}, status=202)


@csrf_exempt
def onboarding_confirm_view(request):
    if request.method != "POST": return JsonResponse({"error": "Method not allowed"}, status=405)
    data = parse_json_body(request)
    token_hash = hashlib.sha256(str(data.get("token", "")).encode()).hexdigest()
    invitation = OnboardingInvitationModel.objects.select_related("user").filter(token_hash=token_hash, used_at__isnull=True, expires_at__gt=timezone.now()).first()
    if not invitation: return JsonResponse({"error": "Invalid invitation"}, status=400)
    password = data.get("password", "")
    try:
        if len(password) < 10: raise DjangoValidationError("weak")
        validate_password(password, invitation.user)
    except DjangoValidationError: return JsonResponse({"error": "Invalid invitation or weak password"}, status=400)
    with transaction.atomic():
        invitation = OnboardingInvitationModel.objects.select_for_update().get(id=invitation.id)
        if invitation.used_at or invitation.expires_at <= timezone.now(): return JsonResponse({"error": "Invalid invitation"}, status=400)
        invitation.user.set_password(password); invitation.user.save(update_fields=["password"])
        invitation.used_at = timezone.now(); invitation.save(update_fields=["used_at"])
    return JsonResponse({"message": "Password set"})
