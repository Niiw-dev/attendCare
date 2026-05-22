from datetime import timedelta
from django.utils import timezone

from .models import (Event, EventMinistry, RecurringEvent)
from django.core.cache import cache


def generate_missing_events():
    alreadyGenerated = cache.get('events_generated')

    if alreadyGenerated:
        return
    
    today = timezone.localdate()
    endDate = today + timedelta(days=30)
    recurringEvents = RecurringEvent.objects.filter(isActive=True)

    for recurring in recurringEvents:
        currentDate = today

        while currentDate <= endDate:
            if currentDate.weekday() == recurring.weekday:
                alreadyExists = Event.objects.filter(name=recurring.name, 
                                                     startDate__date=currentDate
                                                     ).exists()

                if not alreadyExists:
                    startDatetime = timezone.make_aware(
                        timezone.datetime.combine(currentDate, recurring.startTime)
                    )

                    endDatetime = timezone.make_aware(
                        timezone.datetime.combine(currentDate, recurring.endTime)
                    )

                    event = Event.objects.create(
                        name=recurring.name,
                        eventType=recurring.eventType,
                        startDate=startDatetime,
                        endDate=endDatetime,
                        leaderMinistry=recurring.leaderMinistry,
                        status=recurring.status
                    )

                    ministries = recurring.ministries.all()

                    for ministry in ministries:
                        EventMinistry.objects.create(event=event, ministry=ministry)

            currentDate += timedelta(days=1)

    cache.set('events_generated', True, timeout=60 * 60)