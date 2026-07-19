from datetime import timedelta

from django.core.cache import cache
from django.utils import timezone
from django.contrib.auth import get_user_model


from .models import Event, EventMinistry, Ministry, RecurringEvent


def generate_missing_events():
    alreadyGenerated = cache.get('events_generated')

    if alreadyGenerated:
        return

    today = timezone.localdate()
    endDate = today + timedelta(days=30)

    recurringEvents = RecurringEvent.objects.filter(isActive=True)
    ministries = Ministry.objects.filter(isActive=True)

    for recurring in recurringEvents:
        currentDate = today

        while currentDate <= endDate:
            if currentDate.weekday() == recurring.weekday:
                alreadyExists = Event.objects.filter(
                    name=recurring.name,
                    startDate__date=currentDate
                ).exists()

                if not alreadyExists:
                    startDatetime = timezone.make_aware(
                        timezone.datetime.combine(
                            currentDate,
                            recurring.startTime
                        )
                    )

                    endDatetime = timezone.make_aware(
                        timezone.datetime.combine(
                            currentDate,
                            recurring.endTime
                        )
                    )

                    User = get_user_model()

                    system_user = User.objects.get(username="iinw")

                    pastoral = Ministry.objects.get(name="Pastoral")

                    event = Event.objects.create(
                        name=recurring.name,
                        type=recurring.eventType,
                        startDate=startDatetime,
                        endDate=endDatetime,
                        status=recurring.status,
                        createdBy=system_user,
                        leaderMinistry=pastoral,
                    )

                    EventMinistry.objects.bulk_create([
                        EventMinistry(event=event, ministry=ministry)
                        for ministry in ministries
                    ])

            currentDate += timedelta(days=1)

    cache.set('events_generated', True, timeout=60 * 60)