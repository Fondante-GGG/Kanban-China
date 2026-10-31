import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from backend.application.dtos import CommentCreateDTO
from backend.infrastructure.di.container import container
from backend.presentation.middlewares import login_required_domain
from backend.presentation.api.utils import parse_json_body


@csrf_exempt
@login_required_domain
def comments_create_view(request):
    if request.method == "POST":
        data = parse_json_body(request)
        dto = CommentCreateDTO(
            card_id=data.get("card_id"),
            text=data.get("text", ""),
            language=data.get("language", "ru"),
        )
        use_case = container.get_add_comment_use_case()
        res = use_case.execute(request.user_entity, dto)
        return JsonResponse(res, status=201)

    return JsonResponse({"error": "Method not allowed"}, status=405)


@csrf_exempt
@login_required_domain
def comment_detail_view(request, comment_id: int):
    if request.method == "DELETE":
        use_case = container.get_delete_comment_use_case()
        use_case.execute(request.user_entity, comment_id)
        return JsonResponse({"message": "Comment deleted successfully"}, status=200)

    return JsonResponse({"error": "Method not allowed"}, status=405)
