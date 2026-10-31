import os
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.http import JsonResponse, FileResponse
from django.views.decorators.csrf import csrf_exempt
from backend.infrastructure.di.container import container
from backend.presentation.middlewares import login_required_domain
from backend.domain.exceptions import EntityNotFoundException, PermissionDeniedException, ValidationException
from backend.infrastructure.persistence.models import AttachmentModel
from backend.domain.services import AccessPolicyService


private_storage = FileSystemStorage(location=settings.PRIVATE_MEDIA_ROOT)
MAX_ATTACHMENT_SIZE = 15 * 1024 * 1024
ALLOWED_CONTENT_TYPES = {
    "application/pdf", "image/jpeg", "image/png", "image/webp",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/msword", "application/vnd.ms-excel", "text/plain",
}


@csrf_exempt
@login_required_domain
def attachments_upload_view(request):
    if request.method == "POST":
        card_id = request.POST.get("card_id")
        if not card_id:
            return JsonResponse({"error": "card_id is required"}, status=400)
        try:
            card_id = int(card_id)
        except ValueError:
            return JsonResponse({"error": "card_id must be an integer"}, status=400)

        uploaded_file = request.FILES.get("file")
        if not uploaded_file:
            return JsonResponse({"error": "file is required"}, status=400)
        if uploaded_file.size > MAX_ATTACHMENT_SIZE:
            return JsonResponse({"error": "File size must not exceed 15 MB"}, status=400)
        if uploaded_file.content_type not in ALLOWED_CONTENT_TYPES:
            return JsonResponse({"error": "Unsupported file type"}, status=400)

        # Authorize before writing to disk so denied requests cannot create orphan files.
        use_case = container.get_upload_attachment_use_case()
        with container.get_uow() as uow:
            card = uow.cards.get_by_id(card_id)
            if not card:
                raise EntityNotFoundException("Card", card_id)
            column = uow.columns.get_by_id(card.column_id)
            assigned_board_id = uow.users.get_assigned_board_id(request.user_entity.id)
            AccessPolicyService.ensure_can_manage_cards(request.user_entity, column.board_id, assigned_board_id)
        file_path = private_storage.save(os.path.join("attachments", uploaded_file.name), uploaded_file)
        res = use_case.execute(
            current_user=request.user_entity,
            card_id=card_id,
            file_path=file_path,
            file_name=uploaded_file.name,
            file_size=uploaded_file.size,
            content_type=uploaded_file.content_type or "application/octet-stream"
        )
        res["file_path"] = f"/api/attachments/{res['id']}/download"
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


@login_required_domain
def attachment_download_view(request, attachment_id: int):
    try:
        attachment = AttachmentModel.objects.select_related("card__column").get(id=attachment_id)
    except AttachmentModel.DoesNotExist:
        raise EntityNotFoundException("Attachment", attachment_id)
    assigned_board_id = container.get_uow().users.get_assigned_board_id(request.user_entity.id)
    AccessPolicyService.ensure_can_view_board(request.user_entity, attachment.card.column.board_id, assigned_board_id)
    if not private_storage.exists(attachment.file_path):
        raise EntityNotFoundException("Attachment file", attachment_id)
    return FileResponse(private_storage.open(attachment.file_path, "rb"), as_attachment=True, filename=attachment.file_name)
