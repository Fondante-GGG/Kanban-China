from backend.application.finance_periods import finance_transaction, require_open_period
from decimal import Decimal, InvalidOperation
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from backend.infrastructure.persistence.models import FinanceSalaryModel, FinancePeriodModel, EmployeeModel, MonthlyTimesheetModel
from backend.presentation.api.platform_views import _require
from backend.presentation.api.utils import parse_json_body
from backend.presentation.middlewares import login_required_domain

@csrf_exempt
@login_required_domain
@finance_transaction
def salaries_view(request):
    denied=_require(request,"finance.salary.manage" if request.method!="GET" else "finance.salary.read")
    if denied:return denied
    if request.method=="GET":return JsonResponse({"items":[{"id":x.id,"employee_id":x.employee_id,"year":x.year,"month":x.month,"base_salary":str(x.base_salary),"attendance_deduction":str(x.attendance_deduction),"kpi_bonus":str(x.kpi_bonus),"total_pay":str(x.total_pay),"status":x.status} for x in FinanceSalaryModel.objects.all()]})
    if request.method!="POST":return JsonResponse({"error":"Method not allowed"},status=405)
    b=parse_json_body(request)
    try:
      employee=EmployeeModel.objects.get(id=b["employee_id"],status="active");year=int(b["year"]);month=int(b["month"]);base=Decimal(str(b["base_salary"]));deduct=Decimal(str(b.get("attendance_deduction",0)));bonus=Decimal(str(b.get("kpi_bonus",0)));other=Decimal(str(b.get("other_adjustment",0)))
    except (KeyError,ValueError,InvalidOperation,EmployeeModel.DoesNotExist):return JsonResponse({"error":"valid active employee, period and amounts are required"},status=400)
    if not 1<=year<=9999 or not 1<=month<=12:return JsonResponse({"error":"invalid financial period"},status=400)
    require_open_period(year,month)
    if not MonthlyTimesheetModel.objects.filter(employee=employee,year=year,month=month,status="confirmed").exists(): return JsonResponse({"error":"Confirmed monthly timesheet is required before payroll"},status=409)
    total=base-deduct+bonus+other
    if total<0:return JsonResponse({"error":"total pay cannot be negative"},status=400)
    x=FinanceSalaryModel.objects.create(employee=employee,year=year,month=month,base_salary=base,attendance_deduction=deduct,kpi_bonus=bonus,other_adjustment=other,total_pay=total,currency=str(b.get("currency","KGS")).upper(),created_by_id=request.user_entity.id)
    return JsonResponse({"id":x.id,"total_pay":str(x.total_pay),"status":x.status},status=201)
