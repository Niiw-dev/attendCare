from django.db import models

from ministries.models import Ministry
from users.models import User
from datetime import time



class EventType(models.Model):
    description = models.TextField(blank=True,null=True)
    name = models.CharField(max_length=100)
    isActive = models.BooleanField(default=True)

    def __str__(self):
        return self.name



class EventStatus(models.Model):
    name = models.CharField(max_length=100)
    color = models.CharField(max_length=20, null=True,blank=True)
    isActive = models.BooleanField(default=True)

    def __str__(self):
        return self.name



class Event(models.Model):
    name = models.CharField(max_length=255)
    type = models.ForeignKey(EventType, on_delete=models.PROTECT, related_name='events')
    leaderMinistry = models.ForeignKey(Ministry, on_delete=models.PROTECT,
                                        related_name='leader_events')
    startDate = models.DateTimeField()
    endDate = models.DateTimeField()
    status = models.ForeignKey(EventStatus, on_delete=models.PROTECT, related_name='events')
    createdBy = models.ForeignKey(User, on_delete=models.PROTECT)
    createdAt = models.DateTimeField(auto_now_add=True)
    updatedAt = models.DateTimeField(auto_now=True)
    ministries = models.ManyToManyField(Ministry, through='EventMinistry', related_name='events')

    def __str__(self):
        return self.name



class EventMinistry(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    ministry = models.ForeignKey(Ministry, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('event', 'ministry')



class RecurringEvent(models.Model):
    WEEKDAYS = [
        (0, 'Lunes'),
        (1, 'Martes'),
        (2, 'Miércoles'),
        (3, 'Jueves'),
        (4, 'Viernes'),
        (5, 'Sábado'),
        (6, 'Domingo'),
    ]

    name = models.CharField(max_length=150)
    weekday = models.IntegerField(choices=WEEKDAYS)
    startTime = models.TimeField()
    endTime = models.TimeField()
    eventType = models.ForeignKey('EventType', on_delete=models.PROTECT)
    status = models.ForeignKey('EventStatus', on_delete=models.PROTECT)
    leaderMinistry = models.ForeignKey(Ministry, on_delete=models.PROTECT, related_name='leader_recurring_events')
    ministries = models.ManyToManyField(Ministry, through='RecurringEventMinistry', related_name='recurring_events')
    isActive = models.BooleanField(default=True)

    def __str__(self):
        return self.name



class RecurringEventMinistry(models.Model):
    recurringEvent = models.ForeignKey(RecurringEvent, on_delete=models.CASCADE)
    ministry = models.ForeignKey(Ministry, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('recurringEvent', 'ministry')