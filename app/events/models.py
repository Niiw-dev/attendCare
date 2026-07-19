from django.db import models
from django.utils import timezone

from ministries.models import Ministry
from servers.models import Server
from users.models import User
from datetime import time



class EventType(models.Model):
    description = models.TextField(blank=True,null=True)
    name = models.CharField(max_length=100)
    isActive = models.BooleanField(default=True)

    def __str__(self):
        return self.name



class EventStatus(models.Model):
    CODE_CHOICES = [
        ('PROGRAMADO', 'Programado'),
        ('ACTIVO', 'Activo'),
        ('FINALIZADO', 'Finalizado'),
        ('RECONCILIADO', 'Reconciliado'),
        ('CANCELADO', 'Cancelado'),
        ('INTEGRIDAD_VULNERADA', 'Integridad Vulnerada'),
    ]

    name = models.CharField(max_length=100)
    code = models.CharField(max_length=50, unique=True, null=True, blank=True)
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

    def update_status(self):
        if self.status.code in ('RECONCILIADO', 'CANCELADO'):
            return

        now = timezone.now()
        if now >= self.endDate:
            new_code = 'FINALIZADO'
        elif now >= self.startDate:
            new_code = 'ACTIVO'
        else:
            new_code = 'PROGRAMADO'

        if self.status.code != new_code:
            self.status = EventStatus.objects.get(code=new_code)
            self.save(update_fields=['status'])

    def __str__(self):
        return self.name



class EventMinistry(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    ministry = models.ForeignKey(Ministry, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('event', 'ministry')



class Assignment(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='assignments')
    server = models.ForeignKey(Server, on_delete=models.CASCADE, related_name='assignments')
    ministry = models.ForeignKey(Ministry, on_delete=models.CASCADE)
    assignedBy = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    createdAt = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('event', 'server')

    def __str__(self):
        return f'{self.server} -> {self.event}'



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
    isActive = models.BooleanField(default=True)

    def __str__(self):
        return self.name



class Attendance(models.Model):
    server = models.ForeignKey(Server, on_delete=models.CASCADE, related_name='attendances')
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='attendances')
    ministry = models.ForeignKey(Ministry, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)
    checkOutTime = models.DateTimeField(null=True, blank=True)
    integrityHash = models.CharField(max_length=128, editable=False)

    class Meta:
        unique_together = ('server', 'event')

    def __str__(self):
        return f'{self.server} @ {self.event}'

    def save(self, *args, **kwargs):
        import hashlib
        ts = (self.timestamp or timezone.now()).isoformat()
        co = self.checkOutTime.isoformat() if self.checkOutTime else ''
        raw = f'{self.server_id}:{self.event_id}:{ts}:{co}'
        self.integrityHash = hashlib.sha256(raw.encode()).hexdigest()
        super().save(*args, **kwargs)



class KioskoAttempt(models.Model):
    server = models.ForeignKey(Server, on_delete=models.CASCADE, related_name='kiosko_attempts')
    ipAddress = models.GenericIPAddressField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    successful = models.BooleanField(default=False)

    class Meta:
        ordering = ['-timestamp']



class Reconciliation(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='reconciliations')
    executedAt = models.DateTimeField(auto_now_add=True)
    executedBy = models.ForeignKey(User, on_delete=models.PROTECT)

    class Meta:
        unique_together = ('event',)

    def __str__(self):
        return f'Reconciliación {self.event}'



class ReconciliationDetail(models.Model):
    CLASSIFICATION_CHOICES = [
        ('ASSIGNED', 'Asistió (asignado)'),
        ('VOLUNTEER', 'Voluntario'),
        ('ABSENT', 'Ausente'),
        ('INCOMPLETE', 'Ingresó sin registrar salida'),
        ('REPLACEMENT', 'Reemplazó'),
    ]

    reconciliation = models.ForeignKey(Reconciliation, on_delete=models.CASCADE, related_name='details')
    server = models.ForeignKey(Server, on_delete=models.CASCADE, related_name='reconciliation_details')
    classification = models.CharField(max_length=20, choices=CLASSIFICATION_CHOICES)
    replacedServer = models.ForeignKey(Server, on_delete=models.SET_NULL, null=True, blank=True, related_name='replaced_by')

    class Meta:
        unique_together = ('reconciliation', 'server')

    def __str__(self):
        return f'{self.server}: {self.classification}'



class AuditLog(models.Model):
    ACTION_CHOICES = [
        ('ATTENDANCE_REGISTERED', 'Registro de asistencia'),
        ('RECONCILIATION_EXECUTED', 'Reconciliación ejecutada'),
        ('RECONCILIATION_REPLACEMENT', 'Reemplazo registrado'),
    ]

    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    table = models.CharField(max_length=50)
    recordId = models.IntegerField()
    performedBy = models.CharField(max_length=100, null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    previousHash = models.CharField(max_length=128, null=True, blank=True)
    currentHash = models.CharField(max_length=128, editable=False)
    details = models.JSONField(null=True, blank=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f'{self.action} #{self.recordId}'

    def save(self, *args, **kwargs):
        import hashlib
        last = AuditLog.objects.order_by('-id').first()
        self.previousHash = last.currentHash if last else '0' * 64
        ts = (self.timestamp or timezone.now()).replace(microsecond=0).isoformat()
        raw = f'{self.action}:{self.table}:{self.recordId}:{self.previousHash}:{ts}'
        self.currentHash = hashlib.sha256(raw.encode()).hexdigest()
        super().save(*args, **kwargs)
