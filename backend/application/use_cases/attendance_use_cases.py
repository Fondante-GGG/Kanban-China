import math
import ipaddress
from datetime import datetime, date, time
from typing import Optional, List, Dict, Any
from django.utils import timezone

from backend.domain.entities import (
    User, Office, WorkSchedule, AttendanceRecord, Absence, LocationLog, Consent, Notification
)
from backend.domain.value_objects import (
    RoleType, AttendanceRecordType, VerificationResult, AbsenceCategory, AbsenceType, LocationSource
)
from backend.domain.exceptions import (
    ValidationException, PermissionDeniedException, EntityNotFoundException
)
from backend.application.interfaces.uow import IUnitOfWork
from backend.application.dtos import (
    CheckInDTO, CheckOutDTO, LeaveAbsenceDTO, LocationLogDTO,
    AttendanceRecordEditDTO, ConsentDTO, DayStatusDTO, OfficeDTO, WorkScheduleDTO
)


def calculate_distance_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Haversine formula to calculate the great-circle distance between two points in meters"""
    R = 6371000.0  # Earth radius in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = math.sin(delta_phi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return R * c


def is_ip_in_subnet(client_ip: Optional[str], subnet_str: str) -> bool:
    if not client_ip or not subnet_str:
        return True
    try:
        # Check against comma separated entries
        allowed_entries = [s.strip() for s in subnet_str.split(",") if s.strip()]
        client_addr = ipaddress.ip_address(client_ip)
        for entry in allowed_entries:
            try:
                if "/" in entry:
                    if client_addr in ipaddress.ip_network(entry, strict=False):
                        return True
                else:
                    if client_addr == ipaddress.ip_address(entry):
                        return True
            except ValueError:
                continue
        # Also allow localhost in dev
        if client_ip in ("127.0.0.1", "::1", "localhost"):
            return True
        return False
    except ValueError:
        return True


class GetAttendanceStatusUseCase:
    def __init__(self, uow: IUnitOfWork):
        self.uow = uow

    def execute(self, current_user: User) -> Dict[str, Any]:
        with self.uow:
            today = timezone.localdate()
            now = timezone.now()

            # Today's records
            records = self.uow.attendance_records.list_for_user_date(current_user.id, today)
            latest_record = self.uow.attendance_records.get_latest_for_user(current_user.id)

            # Determine check-in status
            is_checked_in = False
            last_check_in_time = None
            last_check_out_time = None

            for r in records:
                if r.record_type == AttendanceRecordType.CHECK_IN.value:
                    is_checked_in = True
                    last_check_in_time = r.timestamp.isoformat()
                elif r.record_type == AttendanceRecordType.CHECK_OUT.value:
                    is_checked_in = False
                    last_check_out_time = r.timestamp.isoformat()

            # Active break
            active_break = self.uow.absences.get_active_break_for_user(current_user.id)
            active_break_data = None
            if active_break:
                active_break_data = {
                    "id": active_break.id,
                    "absence_type": active_break.absence_type,
                    "start_time": active_break.start_time.isoformat(),
                    "reason": active_break.reason,
                    "comment": active_break.comment,
                }

            # Day status (vacation, sick leave, etc.)
            day_status = self.uow.absences.get_active_day_status_for_user(current_user.id, today)
            day_status_data = None
            if day_status:
                day_status_data = {
                    "id": day_status.id,
                    "absence_type": day_status.absence_type,
                    "start_time": day_status.start_time.isoformat(),
                    "end_time": day_status.end_time.isoformat() if day_status.end_time else None,
                    "reason": day_status.reason,
                }

            # Consent
            consent = self.uow.consents.get_for_user(current_user.id)
            is_consent_granted = consent.is_granted if consent else False

            # Office
            offices = self.uow.offices.list_all()
            if not offices:
                # Create default office if empty
                default_office = self.uow.offices.create(
                    Office(
                        id=None,
                        name="Главный офис",
                        address="ул. Мухаммеда Али Джиннаха, 15/1",
                        latitude=40.512143,
                        longitude=72.808202,
                        radius_meters=100,
                        ip_subnet="",
                        is_ip_check_enabled=False
                    )
                )
                offices = [default_office]
            office = offices[0]

            # Work Schedule
            schedule = self.uow.work_schedules.get_for_user(current_user.id, current_user.department_id)
            if not schedule:
                schedule = self.uow.work_schedules.create(
                    WorkSchedule(
                        id=None,
                        name="Стандартный график 9:00 - 18:00",
                        start_time="09:00",
                        end_time="18:00",
                        break_duration_minutes=60,
                        timezone="Asia/Bishkek",
                        is_active=True
                    )
                )

            # Reminder check: if checked in and current time > schedule end_time + 30 min, flag reminder
            forgot_checkout_reminder = False
            try:
                sched_end_h, sched_end_m = [int(x) for x in schedule.end_time.split(":")[:2]]
                sched_end_dt = timezone.now().replace(hour=sched_end_h, minute=sched_end_m, second=0)
                if is_checked_in and timezone.now() > sched_end_dt:
                    diff_mins = (timezone.now() - sched_end_dt).total_seconds() / 60
                    if diff_mins > 30:
                        forgot_checkout_reminder = True
            except Exception:
                pass

            return {
                "is_checked_in": is_checked_in,
                "last_check_in_time": last_check_in_time,
                "last_check_out_time": last_check_out_time,
                "active_break": active_break_data,
                "day_status": day_status_data,
                "is_consent_granted": is_consent_granted,
                "forgot_checkout_reminder": forgot_checkout_reminder,
                "office": {
                    "id": office.id,
                    "name": office.name,
                    "address": office.address,
                    "latitude": office.latitude,
                    "longitude": office.longitude,
                    "radius_meters": office.radius_meters,
                    "is_ip_check_enabled": office.is_ip_check_enabled,
                },
                "schedule": {
                    "id": schedule.id,
                    "name": schedule.name,
                    "start_time": schedule.start_time,
                    "end_time": schedule.end_time,
                    "break_duration_minutes": schedule.break_duration_minutes,
                    "timezone": schedule.timezone,
                }
            }


class CheckInUseCase:
    def __init__(self, uow: IUnitOfWork):
        self.uow = uow

    def execute(self, current_user: User, dto: CheckInDTO) -> Dict[str, Any]:
        dist_meters = 0.0
        is_within_radius = True
        rejection_reason = ""
        is_rejected = False
        record_id = None
        record_ts = None
        office_name = ""

        with self.uow:
            # 1. Resolve Office
            offices = self.uow.offices.list_all()
            if not offices:
                office = self.uow.offices.create(
                    Office(
                        id=None,
                        name="Главный офис",
                        address="ул. Мухаммеда Али Джиннаха, 15/1",
                        latitude=40.512143,
                        longitude=72.808202,
                        radius_meters=100,
                    )
                )
            elif dto.office_id:
                office = self.uow.offices.get_by_id(dto.office_id) or offices[0]
            else:
                office = offices[0]
            office_name = office.name

            # 2. Check geolocation
            if dto.latitude is not None and dto.longitude is not None:
                dist_meters = calculate_distance_meters(
                    dto.latitude, dto.longitude,
                    office.latitude, office.longitude
                )
                if dist_meters > office.radius_meters:
                    is_within_radius = False
                    rejection_reason = (
                        f"Вне радиуса офиса {office.name}: расстояние {int(dist_meters)} м, "
                        f"допустимый радиус {office.radius_meters} м."
                    )
            else:
                is_within_radius = False
                rejection_reason = "Координаты геолокации не переданы устройством."

            # 3. Check IP address if enabled
            if office.is_ip_check_enabled and dto.ip_address and office.ip_subnet:
                if not is_ip_in_subnet(dto.ip_address, office.ip_subnet):
                    is_within_radius = False
                    rejection_reason += f" Неверный IP сети офиса ({dto.ip_address})."

            now = timezone.now()

            # Record in database (even if rejected, for audit/compliance!)
            record = self.uow.attendance_records.create(
                AttendanceRecord(
                    id=None,
                    user_id=current_user.id,
                    office_id=office.id,
                    record_type=AttendanceRecordType.CHECK_IN.value,
                    timestamp=now,
                    latitude=dto.latitude,
                    longitude=dto.longitude,
                    accuracy_meters=dto.accuracy_meters,
                    is_within_radius=is_within_radius,
                    ip_address=dto.ip_address,
                    verification_result=VerificationResult.VERIFIED.value if is_within_radius else VerificationResult.REJECTED.value,
                    rejection_reason=rejection_reason,
                )
            )
            record_id = record.id
            record_ts = record.timestamp.isoformat()

            if not is_within_radius:
                is_rejected = True
            else:
                # End any active break if returning directly with check-in
                active_break = self.uow.absences.get_active_break_for_user(current_user.id)
                if active_break:
                    active_break.end_time = now
                    self.uow.absences.update(active_break)

                # Notify all active General Directors about check-in
                try:
                    all_users = self.uow.users.list_all()
                    director_users = [
                        u for u in all_users
                        if u.is_general_director and u.is_active and u.id != current_user.id
                    ]
                    if director_users:
                        if current_user.is_manager:
                            role_label = "Руководитель"
                        elif current_user.is_general_director:
                            role_label = "Генеральный директор"
                        else:
                            role_label = "Сотрудник"

                        dept_str = ""
                        if current_user.department_id:
                            dept = self.uow.departments.get_by_id(current_user.department_id)
                            if dept:
                                dept_str = f" ({dept.name})"

                        local_time = timezone.localtime(record.timestamp)
                        time_str = local_time.strftime("%H:%M")

                        notif_title = "Приход сотрудника в офис"
                        notif_message = (
                            f"{current_user.full_name} [{role_label}{dept_str}] пришёл(ла) в офис "
                            f"«{office_name}» в {time_str}"
                        )

                        for director in director_users:
                            notif = Notification(
                                id=None,
                                user_id=director.id,
                                title=notif_title,
                                message=notif_message,
                                entity_type="attendance",
                                entity_id=record.id,
                                is_read=False,
                            )
                            self.uow.notifications.create(notif)
                except Exception as e:
                    # Non-blocking notification failure
                    pass

        if is_rejected:
            raise ValidationException(rejection_reason)

        return {
            "success": True,
            "message": f"Отметка «Пришёл» успешно зафиксирована ({office_name})",
            "record_id": record_id,
            "timestamp": record_ts,
            "distance_meters": round(dist_meters, 1),
        }


class CheckOutUseCase:
    def __init__(self, uow: IUnitOfWork):
        self.uow = uow

    def execute(self, current_user: User, dto: CheckOutDTO) -> Dict[str, Any]:
        with self.uow:
            offices = self.uow.offices.list_all()
            office = offices[0] if offices else None

            dist_meters = 0.0
            is_within_radius = True
            rejection_reason = ""

            if office and dto.latitude is not None and dto.longitude is not None:
                dist_meters = calculate_distance_meters(
                    dto.latitude, dto.longitude,
                    office.latitude, office.longitude
                )
                if dist_meters > office.radius_meters:
                    is_within_radius = False
                    rejection_reason = f"Отметка ухода вне радиуса ({int(dist_meters)}м)"

            now = timezone.now()

            # Check out record
            record = self.uow.attendance_records.create(
                AttendanceRecord(
                    id=None,
                    user_id=current_user.id,
                    office_id=office.id if office else None,
                    record_type=AttendanceRecordType.CHECK_OUT.value,
                    timestamp=now,
                    latitude=dto.latitude,
                    longitude=dto.longitude,
                    accuracy_meters=dto.accuracy_meters,
                    is_within_radius=is_within_radius,
                    ip_address=dto.ip_address,
                    verification_result=VerificationResult.VERIFIED.value if is_within_radius else VerificationResult.REJECTED.value,
                    rejection_reason=rejection_reason,
                )
            )

            # Also close any active break
            active_break = self.uow.absences.get_active_break_for_user(current_user.id)
            if active_break:
                active_break.end_time = now
                self.uow.absences.update(active_break)

            return {
                "success": True,
                "message": "Отметка «Ушёл» успешно зафиксирована",
                "record_id": record.id,
                "timestamp": record.timestamp.isoformat(),
                "distance_meters": round(dist_meters, 1),
            }


class LeaveAbsenceUseCase:
    """Manual or automatic 'Отлучился' (lunch, business, personal, other)"""
    def __init__(self, uow: IUnitOfWork):
        self.uow = uow

    def execute(self, current_user: User, dto: LeaveAbsenceDTO) -> Dict[str, Any]:
        with self.uow:
            # Check if there is already an active break
            active_break = self.uow.absences.get_active_break_for_user(current_user.id)
            if active_break:
                # Update existing
                active_break.absence_type = dto.absence_type
                active_break.reason = dto.reason
                active_break.comment = dto.comment
                updated = self.uow.absences.update(active_break)
                return {
                    "success": True,
                    "message": "Отлучка обновлена",
                    "absence_id": updated.id,
                }

            now = timezone.now()
            absence = self.uow.absences.create(
                Absence(
                    id=None,
                    user_id=current_user.id,
                    category=AbsenceCategory.BREAK.value,
                    absence_type=dto.absence_type,
                    start_time=now,
                    end_time=None,
                    reason=dto.reason,
                    comment=dto.comment,
                    is_approved=True,
                )
            )

            return {
                "success": True,
                "message": "Отлучка зафиксирована",
                "absence_id": absence.id,
                "start_time": absence.start_time.isoformat(),
            }


class ResumeAbsenceUseCase:
    """'Вернулся' button: finishes active intra-day absence"""
    def __init__(self, uow: IUnitOfWork):
        self.uow = uow

    def execute(self, current_user: User) -> Dict[str, Any]:
        with self.uow:
            active_break = self.uow.absences.get_active_break_for_user(current_user.id)
            if not active_break:
                return {"success": True, "message": "Нет активных отлучек"}

            now = timezone.now()
            active_break.end_time = now
            self.uow.absences.update(active_break)

            duration_min = round((now - active_break.start_time).total_seconds() / 60.0)

            return {
                "success": True,
                "message": f"Возвращение зафиксировано (длительность: {duration_min} мин.)",
                "duration_minutes": duration_min,
            }


class RecordLocationLogUseCase:
    """Background location tracking during work hours with consent and 90-day retention cleanup"""
    def __init__(self, uow: IUnitOfWork):
        self.uow = uow

    def execute(self, current_user: User, dto: LocationLogDTO) -> Dict[str, Any]:
        with self.uow:
            # 1. Check consent: if employee didn't give consent, don't record background tracking
            consent = self.uow.consents.get_for_user(current_user.id)
            if not consent or not consent.is_granted:
                return {
                    "success": False,
                    "ignored": True,
                    "reason": "Consent for location tracking is not granted."
                }

            # 2. Check work schedule: tracking only during working hours
            schedule = self.uow.work_schedules.get_for_user(current_user.id, current_user.department_id)
            now = timezone.now()
            now_time_str = now.strftime("%H:%M")
            if schedule and schedule.is_active:
                if not (schedule.start_time <= now_time_str <= schedule.end_time):
                    return {
                        "success": False,
                        "ignored": True,
                        "reason": "Outside of scheduled working hours."
                    }

            # 3. Check office proximity
            offices = self.uow.offices.list_all()
            is_outside = False
            nearest_office = offices[0] if offices else None
            dist = 0.0

            if nearest_office:
                dist = calculate_distance_meters(
                    dto.latitude, dto.longitude,
                    nearest_office.latitude, nearest_office.longitude
                )
                if dist > nearest_office.radius_meters:
                    is_outside = True

            # 4. Save location log
            self.uow.location_logs.create(
                LocationLog(
                    id=None,
                    user_id=current_user.id,
                    timestamp=now,
                    latitude=dto.latitude,
                    longitude=dto.longitude,
                    accuracy_meters=dto.accuracy_meters,
                    source=dto.source,
                    is_outside_office=is_outside,
                )
            )

            # 5. Auto cleanup older than 90 days (ТЗ: срок хранения геоданных 90 дней)
            self.uow.location_logs.cleanup_older_than(90)

            # 6. If user walked outside office and is checked in and has no active break, flag prompt
            needs_absence_prompt = False
            active_break = self.uow.absences.get_active_break_for_user(current_user.id)
            if is_outside and not active_break:
                # Check if checked in
                latest = self.uow.attendance_records.get_latest_for_user(current_user.id)
                if latest and latest.record_type == AttendanceRecordType.CHECK_IN.value:
                    needs_absence_prompt = True

            return {
                "success": True,
                "is_outside_office": is_outside,
                "distance_meters": round(dist, 1),
                "needs_absence_prompt": needs_absence_prompt,
            }


class ListAttendanceRecordsUseCase:
    """Lists attendance history with RBAC:
    - Employee: only self
    - Manager: self + members of manager's boards
    - Director: everyone
    """
    def __init__(self, uow: IUnitOfWork):
        self.uow = uow

    def execute(
        self,
        current_user: User,
        user_id: Optional[int] = None,
        department_id: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        with self.uow:
            # Determine accessible user IDs based on RBAC
            if current_user.is_employee:
                target_user_ids = [current_user.id]
            elif current_user.is_manager:
                from backend.infrastructure.persistence.models import BoardMemberModel
                manager_board_ids = list(BoardMemberModel.objects.filter(user_id=current_user.id, role="manager").values_list("board_id", flat=True))
                allowed_ids = set(BoardMemberModel.objects.filter(board_id__in=manager_board_ids).values_list("user_id", flat=True))
                allowed_ids.add(current_user.id)
                if user_id:
                    if user_id not in allowed_ids:
                        raise PermissionDeniedException("У вас нет прав на просмотр отметок этого сотрудника.")
                    target_user_ids = [user_id]
                else:
                    target_user_ids = list(allowed_ids)
            else:
                # General Director sees everyone
                if user_id:
                    target_user_ids = [user_id]
                elif department_id:
                    target_user_ids = [u.id for u in self.uow.users.list_all(department_id=department_id)]
                else:
                    target_user_ids = None  # All users

            records = self.uow.attendance_records.list_records(
                user_ids=target_user_ids,
                start_date=start_date,
                end_date=end_date,
            )

            result = []
            for r in records:
                result.append({
                    "id": r.id,
                    "user_id": r.user_id,
                    "user_full_name": r.user_full_name or "Сотрудник",
                    "user_email": r.user_email or "",
                    "record_type": r.record_type,
                    "timestamp": r.timestamp.isoformat(),
                    "office_name": r.office_name or "Офис",
                    "latitude": r.latitude,
                    "longitude": r.longitude,
                    "accuracy_meters": r.accuracy_meters,
                    "is_within_radius": r.is_within_radius,
                    "verification_result": r.verification_result,
                    "rejection_reason": r.rejection_reason,
                    "is_edited": r.is_edited,
                    "edited_by_name": r.edited_by_name,
                    "edit_reason": r.edit_reason,
                    "original_timestamp": r.original_timestamp.isoformat() if r.original_timestamp else None,
                })
            return result


class EditAttendanceRecordUseCase:
    """Manager or Director manually edits an attendance record with mandatory reason"""
    def __init__(self, uow: IUnitOfWork):
        self.uow = uow

    def execute(self, current_user: User, record_id: int, dto: AttendanceRecordEditDTO) -> Dict[str, Any]:
        with self.uow:
            if current_user.is_employee:
                raise PermissionDeniedException("Сотрудники не могут редактировать отметки посещаемости.")

            record = self.uow.attendance_records.get_by_id(record_id)
            if not record:
                raise EntityNotFoundException("Запись отметки не найдена.")

            if not dto.edit_reason or not dto.edit_reason.strip():
                raise ValidationException("Обязательно укажите причину ручной правки отметки.")

            # If Manager, ensure target user is on manager's board
            if current_user.is_manager:
                from backend.infrastructure.persistence.models import BoardMemberModel
                manager_board_ids = list(BoardMemberModel.objects.filter(user_id=current_user.id, role="manager").values_list("board_id", flat=True))
                allowed_ids = set(BoardMemberModel.objects.filter(board_id__in=manager_board_ids).values_list("user_id", flat=True))
                allowed_ids.add(current_user.id)
                if record.user_id not in allowed_ids:
                    raise PermissionDeniedException("Вы можете исправлять отметки только сотрудников своей доски.")

            new_timestamp = datetime.fromisoformat(dto.timestamp.replace("Z", "+00:00"))

            # Save history
            if not record.is_edited:
                record.original_timestamp = record.timestamp
            record.timestamp = new_timestamp
            record.is_edited = True
            record.edited_by_id = current_user.id
            record.edit_reason = dto.edit_reason.strip()
            record.verification_result = VerificationResult.MANUAL_OVERRIDE.value

            updated = self.uow.attendance_records.update(record)

            return {
                "success": True,
                "message": "Отметка успешно исправлена и сохранена в истории",
                "record_id": updated.id,
                "new_timestamp": updated.timestamp.isoformat(),
                "edited_by": current_user.full_name,
                "edit_reason": updated.edit_reason,
            }


class ManageConsentUseCase:
    def __init__(self, uow: IUnitOfWork):
        self.uow = uow

    def get_status(self, current_user: User) -> Dict[str, Any]:
        with self.uow:
            consent = self.uow.consents.get_for_user(current_user.id)
            return {
                "is_granted": consent.is_granted if consent else False,
                "consent_version": consent.consent_version if consent else "1.0",
                "granted_at": consent.granted_at.isoformat() if (consent and consent.granted_at) else None,
                "revoked_at": consent.revoked_at.isoformat() if (consent and consent.revoked_at) else None,
            }

    def set_consent(self, current_user: User, dto: ConsentDTO) -> Dict[str, Any]:
        with self.uow:
            consent = self.uow.consents.create_or_update(
                user_id=current_user.id,
                is_granted=dto.is_granted,
                consent_version=dto.consent_version,
                consent_text=dto.consent_text,
            )
            return {
                "success": True,
                "is_granted": consent.is_granted,
                "consent_version": consent.consent_version,
            }


class CreateDayStatusUseCase:
    """Sets day status: vacation, sick_leave, business_trip, day_off"""
    def __init__(self, uow: IUnitOfWork):
        self.uow = uow

    def execute(self, current_user: User, dto: DayStatusDTO) -> Dict[str, Any]:
        with self.uow:
            # Check permissions
            target_user_id = dto.user_id or current_user.id
            if target_user_id != current_user.id and current_user.is_employee:
                raise PermissionDeniedException("Сотрудник не может устанавливать статус дня другим сотрудникам.")

            start_dt = datetime.fromisoformat(dto.start_time.replace("Z", "+00:00"))
            end_dt = datetime.fromisoformat(dto.end_time.replace("Z", "+00:00")) if dto.end_time else None

            absence = self.uow.absences.create(
                Absence(
                    id=None,
                    user_id=target_user_id,
                    category=AbsenceCategory.DAY_STATUS.value,
                    absence_type=dto.absence_type,
                    start_time=start_dt,
                    end_time=end_dt,
                    reason=dto.reason,
                    comment=dto.comment,
                    is_approved=True,
                    approved_by_id=current_user.id,
                )
            )

            return {
                "success": True,
                "absence_id": absence.id,
                "message": f"Статус дня успешно назначен ({dto.absence_type})",
            }
