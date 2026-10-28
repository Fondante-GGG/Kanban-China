import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from backend.application.dtos import ChecklistItemCreateDTO
from backend.infrastructure.di.container import container
from backend.infrastructure.persistence.models import CardModel, ChecklistModel
from backend.presentation.middlewares import login_required_domain
from backend.presentation.websockets.broadcaster import broadcast_to_board


@csrf_exempt
@login_required_domain
def checklists_create_view(request):
    if request.method == "POST":
        data = json.loads(request.body.decode("utf-8"))
        dto = ChecklistItemCreateDTO(
            card_id=data.get("card_id"),
            title=data.get("title", ""),
        )
        use_case = container.get_add_checklist_use_case()
        res = use_case.execute(request.user_entity, dto)

        # Broadcast event
        card_obj = CardModel.objects.filter(id=dto.card_id).select_related("column").first()
        if card_obj and card_obj.column:
            broadcast_to_board(card_obj.column.board_id, {
                "type": "checklist_created",
                "card_id": dto.card_id,
                "item": res,
                "user_id": request.user_entity.id,
            })

        return JsonResponse(res, status=201)

    return JsonResponse({"error": "Method not allowed"}, status=405)


@csrf_exempt
@login_required_domain
def checklist_toggle_view(request, item_id: int):
    # Retrieve board_id and card_id before operation
    item_obj = ChecklistModel.objects.filter(id=item_id).select_related("card__column").first()
    board_id = None
    card_id = None
    if item_obj and item_obj.card and item_obj.card.column:
        board_id = item_obj.card.column.board_id
        card_id = item_obj.card_id

    if request.method == "PUT":
        use_case = container.get_toggle_checklist_use_case()
        res = use_case.execute(request.user_entity, item_id)

        if board_id:
            broadcast_to_board(board_id, {
                "type": "checklist_toggled",
                "card_id": card_id,
                "item_id": item_id,
                "is_completed": res.get("is_completed"),
                "user_id": request.user_entity.id,
            })

        return JsonResponse(res, status=200)

    elif request.method == "DELETE":
        use_case = container.get_delete_checklist_use_case()
        use_case.execute(request.user_entity, item_id)

        if board_id:
            broadcast_to_board(board_id, {
                "type": "checklist_deleted",
                "card_id": card_id,
                "item_id": item_id,
                "user_id": request.user_entity.id,
            })

        return JsonResponse({"message": "Checklist item deleted successfully"}, status=200)

    return JsonResponse({"error": "Method not allowed"}, status=405)
