import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from backend.infrastructure.di.container import container
from backend.presentation.middlewares import login_required_domain


@csrf_exempt
@login_required_domain
def notifications_list_view(request):
    if request.method == "GET":
        unread_only = request.GET.get("unread", "false").lower() == "true"
        use_case = container.get_notifications_use_case()
        items = use_case.execute(request.user_entity, unread_only)
        return JsonResponse({"notifications": items}, status=200)

    elif request.method == "POST":
        # Mark as read
        data = {}
        if request.body:
            try:
                data = json.loads(request.body.decode("utf-8"))
            except Exception:
                pass
        notif_id = data.get("notification_id")
        use_case = container.get_mark_notifications_read_use_case()
        use_case.execute(request.user_entity, notif_id)
        return JsonResponse({"message": "Notifications marked as read"}, status=200)

    return JsonResponse({"error": "Method not allowed"}, status=405)
