import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from backend.infrastructure.di.container import container
from backend.presentation.middlewares import login_required_domain


@csrf_exempt
@login_required_domain
def convert_chinese_view(request):
    if request.method == "POST":
        data = json.loads(request.body.decode("utf-8"))
        text = data.get("text", "")
        variant = data.get("variant", "zh-Hans")  # "zh-Hans" or "zh-Hant"
        converted = container.translation_service.convert_chinese(text, variant)
        return JsonResponse({"text": converted, "variant": variant}, status=200)

    return JsonResponse({"error": "Method not allowed"}, status=405)


@csrf_exempt
@login_required_domain
def translate_text_view(request):
    if request.method == "POST":
        data = json.loads(request.body.decode("utf-8"))
        text = data.get("text", "")
        source_lang = data.get("source_lang")
        multilingual = container.translation_service.translate_multilingual(text, source_lang)
        return JsonResponse({"translations": multilingual}, status=200)

    return JsonResponse({"error": "Method not allowed"}, status=405)
