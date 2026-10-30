import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from backend.application.dtos import BoardCreateDTO, BoardUpdateDTO
from backend.infrastructure.di.container import container
from backend.presentation.middlewares import login_required_domain


@csrf_exempt
@login_required_domain
def boards_list_create_view(request):
    if request.method == "GET":
        use_case = container.get_list_boards_use_case()
        boards = use_case.execute(request.user_entity)
        return JsonResponse({"boards": boards}, status=200)

    elif request.method == "POST":
        try:
            data = json.loads(request.body.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON body"}, status=400)
        dto = BoardCreateDTO(
            title=data.get("title", ""),
            department_id=data.get("department_id"),
            background_theme=data.get("background_theme", "gradient-blue"),
            manager_id=data.get("manager_id"),
            employee_ids=data.get("employee_ids", []),
        )
        use_case = container.get_create_board_use_case()
        res = use_case.execute(request.user_entity, dto)
        return JsonResponse(res, status=201)

    return JsonResponse({"error": "Method not allowed"}, status=405)


@csrf_exempt
@login_required_domain
def board_detail_view(request, board_id: int):
    if request.method == "GET":
        search = request.GET.get("search")
        priority = request.GET.get("priority")
        assignee_id = request.GET.get("assignee_id")
        try:
            assignee_id = int(assignee_id) if assignee_id else None
        except ValueError:
            return JsonResponse({"error": "assignee_id must be an integer"}, status=400)

        use_case = container.get_board_details_use_case()
        details = use_case.execute(request.user_entity, board_id, search=search, priority=priority, assignee_id=assignee_id)
        return JsonResponse(details, status=200)

    elif request.method == "PUT":
        try:
            data = json.loads(request.body.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON body"}, status=400)
        dto = BoardUpdateDTO(
            title=data.get("title"),
            department_id=data.get("department_id"),
            background_theme=data.get("background_theme"),
            is_archived=data.get("is_archived"),
            manager_id=data.get("manager_id"),
            employee_ids=data.get("employee_ids"),
        )
        use_case = container.get_update_board_use_case()
        res = use_case.execute(request.user_entity, board_id, dto)
        return JsonResponse(res, status=200)

    elif request.method == "DELETE":
        use_case = container.get_delete_board_use_case()
        use_case.execute(request.user_entity, board_id)
        return JsonResponse({"message": "Board deleted successfully"}, status=200)

    return JsonResponse({"error": "Method not allowed"}, status=405)
