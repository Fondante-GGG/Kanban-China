from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from backend.application.dtos import ReportFilterDTO
from backend.infrastructure.di.container import container
from backend.presentation.middlewares import login_required_domain


@csrf_exempt
@login_required_domain
def analytics_report_view(request):
    if request.method == "GET":
        dept_id = request.GET.get("department_id")
        dept_id = int(dept_id) if dept_id else None
        dto = ReportFilterDTO(
            period=request.GET.get("period", "month"),
            start_date=request.GET.get("start_date"),
            end_date=request.GET.get("end_date"),
            department_id=dept_id
        )
        use_case = container.get_analytics_report_use_case()
        data = use_case.execute(request.user_entity, dto)
        return JsonResponse(data, status=200)

    return JsonResponse({"error": "Method not allowed"}, status=405)


@csrf_exempt
@login_required_domain
def export_report_view(request):
    if request.method == "GET":
        fmt = request.GET.get("format", "xlsx")
        dept_id = request.GET.get("department_id")
        dept_id = int(dept_id) if dept_id else None
        dto = ReportFilterDTO(
            period=request.GET.get("period", "month"),
            start_date=request.GET.get("start_date"),
            end_date=request.GET.get("end_date"),
            department_id=dept_id
        )
        use_case = container.get_export_report_use_case()
        file_bytes, content_type, filename = use_case.execute(request.user_entity, fmt, dto)

        response = HttpResponse(file_bytes, content_type=content_type)
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response

    return JsonResponse({"error": "Method not allowed"}, status=405)
