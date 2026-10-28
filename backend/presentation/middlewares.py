import functools
from django.http import JsonResponse
from backend.domain.exceptions import (
    AuthenticationFailedException, PermissionDeniedException, ValidationException, EntityNotFoundException
)
from backend.infrastructure.di.container import container


def login_required_domain(view_func):
    """Decorator ensuring request has a valid authenticated user_entity"""
    @functools.wraps(view_func)
    def wrapper(request, *args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return JsonResponse({"error": "Authentication required. Missing Bearer token."}, status=401)

        token = auth_header.split(" ", 1)[1].strip()
        try:
            payload = container.jwt_service.verify_token(token)
            user_id = payload.get("sub")
            with container.get_uow() as uow:
                user = uow.users.get_by_id(user_id)
                if not user or not user.is_active:
                    return JsonResponse({"error": "User account not found or inactive."}, status=401)
                request.user_entity = user
        except AuthenticationFailedException as e:
            return JsonResponse({"error": e.message}, status=401)
        except Exception as e:
            return JsonResponse({"error": "Invalid token."}, status=401)

        try:
            return view_func(request, *args, **kwargs)
        except PermissionDeniedException as e:
            return JsonResponse({"error": e.message}, status=403)
        except EntityNotFoundException as e:
            return JsonResponse({"error": e.message}, status=404)
        except ValidationException as e:
            return JsonResponse({"error": e.message}, status=400)
        except Exception as e:
            import traceback
            traceback.print_exc()
            return JsonResponse({"error": str(e)}, status=500)

    return wrapper


class JWTAuthenticationMiddleware:
    """Extracts JWT user and sets request.user_entity if token is provided"""
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        auth_header = request.headers.get("Authorization", "")
        request.user_entity = None
        if auth_header.startswith("Bearer "):
            token = auth_header.split(" ", 1)[1].strip()
            try:
                payload = container.jwt_service.verify_token(token)
                user_id = payload.get("sub")
                with container.get_uow() as uow:
                    user = uow.users.get_by_id(user_id)
                    if user and user.is_active:
                        request.user_entity = user
            except Exception:
                pass
        return self.get_response(request)
