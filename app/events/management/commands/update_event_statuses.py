from django.core.management.base import BaseCommand
from django.utils import timezone

from events.models import Event, EventStatus


class Command(BaseCommand):
    help = 'Actualiza estados de eventos según fecha/hora actual'

    def handle(self, *args, **options):
        now = timezone.now()

        activo = EventStatus.objects.get(code='ACTIVO')
        finalizado = EventStatus.objects.get(code='FINALIZADO')
        programado = EventStatus.objects.get(code='PROGRAMADO')

        finalized = Event.objects.filter(
            endDate__lte=now,
            status__code__in=['PROGRAMADO', 'ACTIVO']
        ).exclude(status__code='RECONCILIADO').update(status=finalizado)

        activated = Event.objects.filter(
            startDate__lte=now,
            endDate__gte=now,
            status__code='PROGRAMADO'
        ).update(status=activo)

        self.stdout.write(self.style.SUCCESS(
            f'Actualizados: {activated} activados, {finalized} finalizados'
        ))
