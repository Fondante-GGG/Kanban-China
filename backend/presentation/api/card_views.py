import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from backend.application.dtos import CardCreateDTO, CardUpdateDTO, CardMoveDTO
from backend.infrastructure.di.container import container
from backend.infrastructure.persistence.models import CardModel, ColumnModel
from backend.presentation.middlewares import login_required_domain
from backend.presentation.websockets.broadcaster import broadcast_to_board
from backend.presentation.api.utils import parse_json_body


@csrf_exempt
@login_required_domain
def cards_create_view(request):
    if request.method == "POST":
        data = parse_json_body(request)
        dto = CardCreateDTO(
            column_id=data.get("column_id"),
            title=data.get("title", ""),
            description=data.get("description", ""),
            language=data.get("language", "ru"),
            priority=data.get("priority", "medium"),
            due_date=data.get("due_date"),
            assignee_ids=data.get("assignee_ids", []),
        )
        use_case = container.get_create_card_use_case()
        res = use_case.execute(request.user_entity, dto)

        # Broadcast real-time event
        col = ColumnModel.objects.filter(id=dto.column_id).first()
        if col:
            broadcast_to_board(col.board_id, {
                "type": "card_created",
                "card_id": res.get("id"),
                "column_id": dto.column_id,
                "user_id": request.user_entity.id,
            })

        return JsonResponse(res, status=201)

    return JsonResponse({"error": "Method not allowed"}, status=405)


@csrf_exempt
@login_required_domain
def card_detail_view(request, card_id: int):
    if request.method == "GET":
        use_case = container.get_card_detail_use_case()
        res = use_case.execute(request.user_entity, card_id)
        return JsonResponse(res, status=200)

    elif request.method == "PUT":
        data = parse_json_body(request)
        dto = CardUpdateDTO(
            title=data.get("title"),
            description=data.get("description"),
            language=data.get("language", "ru"),
            priority=data.get("priority"),
            due_date=data.get("due_date"),
            assignee_ids=data.get("assignee_ids"),
        )
        use_case = container.get_update_card_use_case()
        res = use_case.execute(request.user_entity, card_id, dto)

        # Broadcast update
        card_obj = CardModel.objects.filter(id=card_id).select_related("column").first()
        if card_obj and card_obj.column:
            broadcast_to_board(card_obj.column.board_id, {
                "type": "card_updated",
                "card_id": card_id,
                "column_id": card_obj.column_id,
                "user_id": request.user_entity.id,
            })

        return JsonResponse(res, status=200)

    elif request.method == "DELETE":
        card_obj = CardModel.objects.filter(id=card_id).select_related("column").first()
        board_id = card_obj.column.board_id if card_obj and card_obj.column else None

        use_case = container.get_delete_card_use_case()
        use_case.execute(request.user_entity, card_id)

        if board_id:
            broadcast_to_board(board_id, {
                "type": "card_deleted",
                "card_id": card_id,
                "user_id": request.user_entity.id,
            })

        return JsonResponse({"message": "Card deleted successfully"}, status=200)

    return JsonResponse({"error": "Method not allowed"}, status=405)


@csrf_exempt
@login_required_domain
def card_move_view(request, card_id: int):
    if request.method == "POST":
        data = parse_json_body(request)
        dto = CardMoveDTO(
            target_column_id=data.get("target_column_id"),
            target_order=data.get("target_order", 0)
        )
        use_case = container.get_move_card_use_case()
        res = use_case.execute(request.user_entity, card_id, dto)

        # Broadcast real-time move event to all board clients
        target_col = ColumnModel.objects.filter(id=dto.target_column_id).first()
        if target_col:
            broadcast_to_board(target_col.board_id, {
                "type": "card_moved",
                "card_id": card_id,
                "target_column_id": dto.target_column_id,
                "target_order": dto.target_order,
                "user_id": request.user_entity.id,
            })

        return JsonResponse(res, status=200)

    return JsonResponse({"error": "Method not allowed"}, status=405)
