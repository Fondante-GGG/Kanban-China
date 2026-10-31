import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from backend.application.dtos import UserCreateDTO, UserUpdateDTO
from backend.domain.entities import Department
from backend.infrastructure.di.container import container
from backend.presentation.middlewares import login_required_domain
from backend.presentation.api.utils import parse_json_body


@csrf_exempt
@login_required_domain
def users_list_create_view(request):
    if request.method == "GET":
        dept_id = request.GET.get("department_id")
        try:
            dept_id = int(dept_id) if dept_id else None
        except ValueError:
            return JsonResponse({"error": "department_id must be an integer"}, status=400)
        use_case = container.get_list_users_use_case()
        users = use_case.execute(request.user_entity, dept_id)
        return JsonResponse({"users": users}, status=200)

    elif request.method == "POST":
        data = parse_json_body(request)
        dto = UserCreateDTO(
            email=data.get("email", ""),
            password=data.get("password", ""),
            full_name=data.get("full_name", ""),
            role=data.get("role", "employee"),
            department_id=data.get("department_id"),
            board_id=data.get("board_id"),
            phone=data.get("phone"),
            interface_language=data.get("interface_language", "ru"),
        )
        use_case = container.get_create_user_use_case()
        res = use_case.execute(request.user_entity, dto)
        return JsonResponse(res, status=201)

    return JsonResponse({"error": "Method not allowed"}, status=405)


@csrf_exempt
@login_required_domain
def user_detail_view(request, user_id: int):
    if request.method == "PUT":
        data = parse_json_body(request)
        dto = UserUpdateDTO(
            full_name=data.get("full_name"),
            role=data.get("role"),
            department_id=data.get("department_id"),
            board_id=data.get("board_id"),
            phone=data.get("phone"),
            password=data.get("password"),
            interface_language=data.get("interface_language"),
            is_active=data.get("is_active"),
        )
        use_case = container.get_update_user_use_case()
        res = use_case.execute(request.user_entity, user_id, dto)
        return JsonResponse(res, status=200)

    elif request.method == "DELETE":
        use_case = container.get_delete_user_use_case()
        use_case.execute(request.user_entity, user_id)
        return JsonResponse({"message": "User deleted successfully"}, status=200)

    return JsonResponse({"error": "Method not allowed"}, status=405)


@csrf_exempt
@login_required_domain
def departments_view(request):
    with container.get_uow() as uow:
        if request.method == "GET":
            depts = uow.departments.list_all()
            return JsonResponse({
                "departments": [
                    {"id": d.id, "name": d.name, "created_at": d.created_at.isoformat() if d.created_at else None}
                    for d in depts
                ]
            }, status=200)
        elif request.method == "POST":
            if not request.user_entity.is_general_director:
                return JsonResponse({"error": "Admin privileges required"}, status=403)
            data = parse_json_body(request)
            name = data.get("name", "").strip()
            if not name:
                return JsonResponse({"error": "Department name is required"}, status=400)
            dept = Department(id=None, name=name)
            created = uow.departments.create(dept)
            uow.commit()

            # Ensure default board is linked and return its board_id
            boards = uow.boards.list_all()
            dept_board = next((b for b in boards if b.department_id == created.id and not b.is_archived), None)
            if not dept_board:
                from backend.domain.entities import Board, Column
                from backend.application.use_cases.board_use_cases import DEFAULT_TEMPLATE_COLUMNS
                new_board = Board(
                    id=None,
                    title=created.name,
                    department_id=created.id,
                    background_theme="gradient-blue",
                    is_archived=False,
                )
                created_b = uow.boards.create(new_board)
                for idx, col_template in enumerate(DEFAULT_TEMPLATE_COLUMNS):
                    col = Column(
                        id=None,
                        board_id=created_b.id,
                        title_ru=col_template["ru"],
                        title_zh=col_template["zh"],
                        title_ky=col_template["ky"],
                        original_lang="ru",
                        order=idx,
                    )
                    uow.columns.create(col)
                uow.commit()
                board_id = created_b.id
            else:
                board_id = dept_board.id

            return JsonResponse({"id": created.id, "name": created.name, "board_id": board_id}, status=201)

    return JsonResponse({"error": "Method not allowed"}, status=405)


@csrf_exempt
@login_required_domain
def department_detail_view(request, dept_id: int):
    if not request.user_entity.is_general_director:
        return JsonResponse({"error": "Admin privileges required"}, status=403)
    with container.get_uow() as uow:
        dept = uow.departments.get_by_id(dept_id)
        if not dept:
            return JsonResponse({"error": "Department not found"}, status=404)
        if request.method == "PUT":
            data = parse_json_body(request)
            name = data.get("name", "").strip()
            if not name:
                return JsonResponse({"error": "Department name cannot be empty"}, status=400)
            dept.name = name
            updated = uow.departments.update(dept)
            uow.commit()
            return JsonResponse({"id": updated.id, "name": updated.name}, status=200)
        elif request.method == "DELETE":
            # Clean up associated boards for this department
            boards = uow.boards.list_all(include_archived=True)
            for b in boards:
                if b.department_id == dept_id:
                    uow.boards.delete(b.id)
            uow.departments.delete(dept_id)
            uow.commit()
            return JsonResponse({"message": "Department deleted successfully"}, status=200)

    return JsonResponse({"error": "Method not allowed"}, status=405)
