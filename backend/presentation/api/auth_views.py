import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from backend.application.dtos import LoginInputDTO
from backend.infrastructure.di.container import container
from backend.presentation.middlewares import login_required_domain
from backend.domain.exceptions import AuthenticationFailedException, ValidationException


@csrf_exempt
@require_http_methods(["POST"])
def login_view(request):
    try:
        data = json.loads(request.body.decode("utf-8"))
        dto = LoginInputDTO(
            email=data.get("email", ""),
            password=data.get("password", "")
        )
        use_case = container.get_login_use_case()
        result = use_case.execute(dto)
        return JsonResponse(result, status=200)
    except AuthenticationFailedException as e:
        return JsonResponse({"error": e.message}, status=401)
    except ValidationException as e:
        return JsonResponse({"error": e.message}, status=400)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@csrf_exempt
@require_http_methods(["GET"])
@login_required_domain
def me_view(request):
    use_case = container.get_profile_use_case()
    profile = use_case.execute(request.user_entity.id)
    from backend.infrastructure.persistence.models import SystemPermissionModel
    if request.user_entity.is_general_director:
        from backend.presentation.api.platform_views import ALL_PERMISSIONS
        profile["system_permissions"] = ALL_PERMISSIONS
    else:
        profile["system_permissions"] = list(SystemPermissionModel.objects.filter(roles__user_links__user_id=request.user_entity.id, roles__is_active=True).values_list("code", flat=True).distinct())
    return JsonResponse(profile, status=200)


@csrf_exempt
@require_http_methods(["PUT", "PATCH"])
@login_required_domain
def profile_language_view(request):
    try:
        data = json.loads(request.body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON body"}, status=400)
    try:
        use_case = container.get_update_interface_language_use_case()
        profile = use_case.execute(request.user_entity.id, data.get("interface_language"))
        return JsonResponse(profile, status=200)
    except ValidationException as exc:
        return JsonResponse({"error": exc.message}, status=400)


@csrf_exempt
@require_http_methods(["POST"])
@login_required_domain
def reset_password_view(request):
    try:
        data = json.loads(request.body.decode("utf-8"))
        new_password = data.get("new_password", "")
        target_user_id = data.get("user_id") or request.user_entity.id

        # Non-directors can only change their own password
        if target_user_id != request.user_entity.id and not request.user_entity.is_general_director:
            return JsonResponse({"error": "Permission denied"}, status=403)

        use_case = container.get_reset_password_use_case()
        use_case.execute(target_user_id, new_password)
        return JsonResponse({"message": "Password successfully updated."}, status=200)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)
