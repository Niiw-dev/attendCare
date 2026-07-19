from celery import shared_task
from django.utils import timezone

from .models import Event, EventStatus, Attendance, Reconciliation, ReconciliationDetail, AuditLog
from .services import generate_missing_events
from users.models import User


@shared_task
def update_event_statuses():
    now = timezone.now()

    activo = EventStatus.objects.get(code='ACTIVO')
    finalizado = EventStatus.objects.get(code='FINALIZADO')

    Event.objects.filter(
        endDate__lte=now,
        status__code__in=['PROGRAMADO', 'ACTIVO']
    ).exclude(status__code='RECONCILIADO').update(status=finalizado)

    Event.objects.filter(
        startDate__lte=now,
        endDate__gte=now,
        status__code='PROGRAMADO'
    ).update(status=activo)

    auto_reconcile_events()


@shared_task
def generate_recurring_events():
    generate_missing_events()


def verify_audit_chain():
    import hashlib
    logs = list(AuditLog.objects.order_by('id'))
    prev_hash = '0' * 64

    for log in logs:
        if log.previousHash != prev_hash:
            return False
        ts = log.timestamp.replace(microsecond=0).isoformat() if log.timestamp else ''
        raw = f'{log.action}:{log.table}:{log.recordId}:{log.previousHash}:{ts}'
        expected = hashlib.sha256(raw.encode()).hexdigest()
        if log.currentHash != expected:
            return False
        prev_hash = log.currentHash

    return True


def auto_reconcile_events():
    finalizado = EventStatus.objects.get(code='FINALIZADO')
    reconciliado = EventStatus.objects.get(code='RECONCILIADO')
    integridad_vulnerada = EventStatus.objects.get_or_create(
        code='INTEGRIDAD_VULNERADA',
        defaults={'name': 'Integridad Vulnerada', 'color': '#dc2626', 'isActive': True}
    )[0]

    events = Event.objects.filter(
        status=finalizado
    ).exclude(
        reconciliations__isnull=False
    ).prefetch_related(
        'assignments__server', 'assignments__ministry',
        'attendances__server', 'attendances__ministry'
    )

    if not events.exists():
        return

    system_user = User.objects.filter(role='PASTOR', is_active=True).order_by('id').first()
    if not system_user:
        system_user = User.objects.filter(is_superuser=True).order_by('id').first()
    if not system_user:
        return

    chain_ok = verify_audit_chain()

    for event in events:
        if not chain_ok:
            event.status = integridad_vulnerada
            event.save(update_fields=['status'])
            AuditLog.objects.create(
                action='RECONCILIATION_EXECUTED',
                table='Reconciliation',
                recordId=0,
                performedBy=f'system:{system_user.id}',
                details={
                    'eventId': event.id,
                    'eventName': event.name,
                    'error': 'Cadena de auditoría alterada, no se pudo reconciliar',
                    'autoReconciled': True,
                },
            )
            continue

        assignments = list(event.assignments.all())
        attendances = list(event.attendances.all())

        assigned_ids = {a.server_id for a in assignments}
        attended_ids = {a.server_id for a in attendances}
        volunteer_ids = attended_ids - assigned_ids

        # Build ministry lookup for assignments
        assigned_ministry = {a.server_id: a.ministry_id for a in assignments}

        # Build attendee ministry lookup
        attended_ministry = {a.server_id: a.ministry_id for a in attendances}

        reconciliation = Reconciliation.objects.create(
            event=event,
            executedBy=system_user,
        )

        details_to_create = []
        absent_servers = []

        attendance_map = {a.server_id: a for a in attendances}

        for a in assignments:
            att = attendance_map.get(a.server_id)
            if att is not None and att.checkOutTime is not None:
                classification = 'ASSIGNED'
            elif att is not None:
                classification = 'INCOMPLETE'
            else:
                classification = 'ABSENT'
                absent_servers.append(a)

            details_to_create.append(ReconciliationDetail(
                reconciliation=reconciliation,
                server=a.server,
                classification=classification,
            ))

        # Volunteers who filled in for absent assigned servers (must have checked out)
        used_volunteers = set()
        for absent in absent_servers:
            absent_ministry = assigned_ministry.get(absent.server_id)
            for vid in volunteer_ids - used_volunteers:
                if attended_ministry.get(vid) == absent_ministry:
                    att = attendance_map.get(vid)
                    if att is None or att.checkOutTime is None:
                        continue
                    server_obj = next(a for a in attendances if a.server_id == vid).server
                    details_to_create.append(ReconciliationDetail(
                        reconciliation=reconciliation,
                        server=server_obj,
                        classification='REPLACEMENT',
                        replacedServer=absent.server,
                    ))
                    used_volunteers.add(vid)
                    break

        # Remaining volunteers (not used as replacements)
        for a in attendances:
            if a.server_id in volunteer_ids - used_volunteers:
                classification = 'VOLUNTEER' if a.checkOutTime is not None else 'INCOMPLETE'
                details_to_create.append(ReconciliationDetail(
                    reconciliation=reconciliation,
                    server=a.server,
                    classification=classification,
                ))

        ReconciliationDetail.objects.bulk_create(details_to_create)

        event.status = reconciliado
        event.save(update_fields=['status'])

        AuditLog.objects.create(
            action='RECONCILIATION_EXECUTED',
            table='Reconciliation',
            recordId=reconciliation.id,
            performedBy=f'system:{system_user.id}',
            details={
                'eventId': event.id,
                'eventName': event.name,
                'totalServers': len(details_to_create),
                'autoReconciled': True,
                'replacements': len(used_volunteers),
            },
        )
