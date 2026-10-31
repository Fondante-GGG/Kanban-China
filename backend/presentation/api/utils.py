import json

from backend.domain.exceptions import ValidationException


def parse_json_body(request):
    """Parse object-shaped JSON into a stable 400 domain error."""
    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise ValidationException("Invalid JSON body")
    if not isinstance(payload, dict):
        raise ValidationException("JSON body must be an object")
    return payload
