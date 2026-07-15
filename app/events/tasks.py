from celery import shared_task
from django.utils import timezone

from .models import Event, EventStatus
from .services import generate_missing_events


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


@shared_task
def generate_recurring_events():
    generate_missing_events()
