import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from backend.application.dtos import ColumnCreateDTO, ColumnUpdateDTO, ReorderColumnsDTO
from backend.infrastructure.di.container import container
from backend.infrastructure.persistence.models import ColumnModel
from backend.presentation.middlewares import login_required_domain
from backend.presentation.websockets.broadcaster import broadcast_to_board
from backend.presentation.api.utils import parse_json_body


@csrf_exempt
@login_required_domain
def columns_create_view(request):
    if request.method == "POST":
        data = parse_json_body(request)
        dto = ColumnCreateDTO(
            board_id=data.get("board_id"),
            title=data.get("title", ""),
            language=data.get("language", "ru"),
            order=data.get("order"),
        )
        use_case = container.get_create_column_use_case()
        res = use_case.execute(request.user_entity, dto)

        broadcast_to_board(dto.board_id, {
            "type": "column_created",
            "column": res,
            "board_id": dto.board_id,
            "user_id": request.user_entity.id,
        })

        return JsonResponse(res, status=201)

    return JsonResponse({"error": "Method not allowed"}, status=405)


@csrf_exempt
@login_required_domain
def column_detail_view(request, column_id: int):
    col = ColumnModel.objects.filter(id=column_id).first()
    board_id = col.board_id if col else None

    if request.method == "PUT":
        data = parse_json_body(request)
        dto = ColumnUpdateDTO(
            title=data.get("title"),
            language=data.get("language", "ru"),
            order=data.get("order"),
        )
        use_case = container.get_update_column_use_case()
        res = use_case.execute(request.user_entity, column_id, dto)

        if board_id:
            broadcast_to_board(board_id, {
                "type": "column_updated",
                "column_id": column_id,
                "column": res,
                "board_id": board_id,
                "user_id": request.user_entity.id,
            })

        return JsonResponse(res, status=200)

    elif request.method == "DELETE":
        use_case = container.get_delete_column_use_case()
        use_case.execute(request.user_entity, column_id)

        if board_id:
            broadcast_to_board(board_id, {
                "type": "column_deleted",
                "column_id": column_id,
                "board_id": board_id,
                "user_id": request.user_entity.id,
            })

        return JsonResponse({"message": "Column deleted successfully"}, status=200)

    return JsonResponse({"error": "Method not allowed"}, status=405)


@csrf_exempt
@login_required_domain
def reorder_columns_view(request):
    if request.method == "POST":
        data = parse_json_body(request)
        dto = ReorderColumnsDTO(
            board_id=data.get("board_id"),
            column_orders=data.get("column_orders", [])
        )
        use_case = container.get_reorder_columns_use_case()
        use_case.execute(request.user_entity, dto)

        broadcast_to_board(dto.board_id, {
            "type": "columns_reordered",
            "board_id": dto.board_id,
            "user_id": request.user_entity.id,
        })

        return JsonResponse({"message": "Columns reordered successfully"}, status=200)

    return JsonResponse({"error": "Method not allowed"}, status=405)
