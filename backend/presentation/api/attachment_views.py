import os
from django.conf import settings
from django.core.files.storage import default_storage
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from backend.infrastructure.di.container import container
from backend.presentation.middlewares import login_required_domain


@csrf_exempt
@login_required_domain
def attachments_upload_view(request):
    if request.method == "POST":
        card_id = request.POST.get("card_id")
        if not card_id:
            return JsonResponse({"error": "card_id is required"}, status=400)

        uploaded_file = request.FILES.get("file")
        if not uploaded_file:
            return JsonResponse({"error": "file is required"}, status=400)

        # Store file safely
        save_dir = os.path.join(settings.MEDIA_ROOT, "attachments")
        os.makedirs(save_dir, exist_ok=True)
        file_path = default_storage.save(os.path.join("attachments", uploaded_file.name), uploaded_file)
        full_url = f"/media/{file_path}"

        use_case = container.get_upload_attachment_use_case()
        res = use_case.execute(
            current_user=request.user_entity,
            card_id=int(card_id),
            file_path=full_url,
            file_name=uploaded_file.name,
            file_size=uploaded_file.size,
            content_type=uploaded_file.content_type or "application/octet-stream"
        )
        return JsonResponse(res, status=201)

    return JsonResponse({"error": "Method not allowed"}, status=405)


@csrf_exempt
@login_required_domain
def attachment_detail_view(request, attachment_id: int):
    if request.method == "DELETE":
        use_case = container.get_delete_attachment_use_case()
        use_case.execute(request.user_entity, attachment_id)
        return JsonResponse({"message": "Attachment deleted successfully"}, status=200)

    return JsonResponse({"error": "Method not allowed"}, status=405)
