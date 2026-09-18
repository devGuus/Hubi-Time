"""Composition root: instancia repositories e services e os conecta ao
cliente Supabase singleton. A UI recebe este container (injecao de
dependencia via construtor) em vez de instanciar repositories/services
diretamente - isso mantem a UI livre de acesso a dados/regras de negocio.
"""
from __future__ import annotations

from dataclasses import dataclass

from supabase import Client

from database.supabase_client import get_supabase_client
from repositories.audit_repository import AuditRepository
from repositories.holiday_repository import HolidayRepository
from repositories.notification_repository import NotificationRepository
from repositories.salary_repository import SalaryRepository
from repositories.schedule_repository import ScheduleRepository
from repositories.user_repository import UserRepository
from repositories.work_repository import WorkRepository
from security.session_storage import SessionStorage
from services.audit_service import AuditService
from services.auth_service import AuthService
from services.notification_service import NotificationService
from services.report_service import ReportService
from services.salary_service import SalaryService
from services.schedule_service import ScheduleService
from services.work_service import WorkService


@dataclass
class AppContainer:
    client: Client
    session_storage: SessionStorage

    auth_service: AuthService
    work_service: WorkService
    schedule_service: ScheduleService
    salary_service: SalaryService
    audit_service: AuditService
    notification_service: NotificationService
    report_service: type[ReportService]

    user_repository: UserRepository
    holiday_repository: HolidayRepository


def build_container() -> AppContainer:
    client = get_supabase_client()
    session_storage = SessionStorage()

    return AppContainer(
        client=client,
        session_storage=session_storage,
        auth_service=AuthService(client, session_storage),
        work_service=WorkService(WorkRepository(client)),
        schedule_service=ScheduleService(ScheduleRepository(client)),
        salary_service=SalaryService(SalaryRepository(client)),
        audit_service=AuditService(WorkRepository(client), AuditRepository(client)),
        notification_service=NotificationService(NotificationRepository(client)),
        report_service=ReportService,
        user_repository=UserRepository(client),
        holiday_repository=HolidayRepository(client),
    )
