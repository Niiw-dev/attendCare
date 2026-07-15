from rest_framework import serializers
from events.models import (Event, EventMinistry, EventType, EventStatus, Assignment,
                           Attendance, Reconciliation, ReconciliationDetail, AuditLog)
from ministries.models import Ministry
from servers.models import Server
from .models import RecurringEvent


class EventSerializer(serializers.ModelSerializer):
    ministryIds = serializers.ListField(child=serializers.IntegerField(), write_only=True)
    ministries = serializers.SerializerMethodField()
    assignmentServerIds = serializers.ListField(child=serializers.IntegerField(), write_only=True, required=False)
    typeData = serializers.SerializerMethodField()
    statusData = serializers.SerializerMethodField()
    leaderMinistryData = serializers.SerializerMethodField()
    assignmentCount = serializers.SerializerMethodField()
    assignments = serializers.SerializerMethodField()

    class Meta:
        model = Event
        fields = ['id', 'name', 'type', 'typeData', 'status', 'statusData', 'startDate',
                  'endDate', 'leaderMinistry', 'leaderMinistryData', 'ministries', 'ministryIds',
                  'assignmentServerIds', 'assignments', 'createdBy', 'createdAt', 'assignmentCount']
        read_only_fields = ['createdBy', 'createdAt', 'assignmentCount', 'assignments']

    def get_typeData(self, obj):
        return {'id': obj.type.id, 'name': obj.type.name}

    def get_statusData(self, obj):
        return {'id': obj.status.id, 'name': obj.status.name}

    def get_leaderMinistryData(self, obj):
        return {'id': obj.leaderMinistry.id, 'name': obj.leaderMinistry.name}

    def get_ministries(self, obj):
        return [{'id': m.id, 'name': m.name} for m in obj.ministries.all()]

    def get_assignmentCount(self, obj):
        return obj.assignments.count()

    def get_assignments(self, obj):
        qs = obj.assignments.select_related('server', 'ministry').all()
        return AssignmentSerializer(qs, many=True).data

    def validate(self, attrs):
        startDate = attrs.get('startDate')
        endDate = attrs.get('endDate')
        ministryIds = attrs.get('ministryIds', [])
        leaderMinistry = attrs.get('leaderMinistry')

        if startDate >= endDate:
            raise serializers.ValidationError('La fecha de inicio debe ser menor a la fecha final')
        if len(ministryIds) == 0:
            raise serializers.ValidationError('Debe seleccionar al menos un ministerio')
        if leaderMinistry and leaderMinistry.id not in ministryIds:
            raise serializers.ValidationError('El ministerio líder debe estar entre los participantes')
        return attrs

    def create(self, validatedData):
        ministryIds = validatedData.pop('ministryIds', [])
        assignmentServerIds = validatedData.pop('assignmentServerIds', [])
        request = self.context.get('request')
        validatedData['createdBy'] = request.user
        validatedData['status'] = EventStatus.objects.get(code='PROGRAMADO')
        event = Event.objects.create(**validatedData)
        self.assignMinistries(event, ministryIds)
        self.assignServers(event, assignmentServerIds, ministryIds)
        return event

    def update(self, instance, validatedData):
        if instance.status.code in ('FINALIZADO', 'RECONCILIADO', 'CANCELADO'):
            raise serializers.ValidationError('No se puede editar un evento finalizado, reconciliado o cancelado')
        ministryIds = validatedData.pop('ministryIds', None)
        assignmentServerIds = validatedData.pop('assignmentServerIds', None)
        for key, value in validatedData.items():
            setattr(instance, key, value)
        instance.save()
        if ministryIds is not None:
            EventMinistry.objects.filter(event=instance).delete()
            self.assignMinistries(instance, ministryIds)
        if assignmentServerIds is not None:
            Assignment.objects.filter(event=instance).delete()
            self.assignServers(instance, assignmentServerIds, ministryIds or [])
        return instance

    def assignMinistries(self, event, ministryIds):
        ministries = Ministry.objects.filter(id__in=ministryIds, isActive=True)
        for ministry in ministries:
            EventMinistry.objects.create(event=event, ministry=ministry)

    def assignServers(self, event, serverIds, ministryIds):
        if not serverIds:
            return
        servers = Server.objects.filter(id__in=serverIds, isActive=True)
        ministryIds_set = set(ministryIds)
        for server in servers:
            server_ministry_ids = set(server.ministries.filter(isActive=True).values_list('id', flat=True))
            common = ministryIds_set & server_ministry_ids
            if common:
                Assignment.objects.create(event=event, server=server, ministry_id=list(common)[0])


class AssignmentSerializer(serializers.ModelSerializer):
    serverData = serializers.SerializerMethodField()
    ministryData = serializers.SerializerMethodField()

    class Meta:
        model = Assignment
        fields = ['id', 'event', 'server', 'serverData', 'ministry', 'ministryData',
                  'assignedBy', 'createdAt']
        read_only_fields = ['assignedBy', 'createdAt']

    def get_serverData(self, obj):
        return {'id': obj.server.id, 'firstName': obj.server.firstName, 'lastName': obj.server.lastName}

    def get_ministryData(self, obj):
        return {'id': obj.ministry.id, 'name': obj.ministry.name}

    def validate(self, attrs):
        event = attrs.get('event') or self.instance.event
        server = attrs.get('server')
        ministry = attrs.get('ministry')

        if event.status.code in ('FINALIZADO', 'RECONCILIADO', 'CANCELADO'):
            raise serializers.ValidationError('No se pueden modificar asignaciones en eventos finalizados, reconciliados o cancelados')

        if event.type.name != 'ORACION':
            event_ministry_ids = set(event.ministries.values_list('id', flat=True))
            if ministry.id not in event_ministry_ids:
                raise serializers.ValidationError('El ministerio debe ser uno de los ministerios participantes del evento')
            server_ministry_ids = set(server.ministries.values_list('id', flat=True))
            if ministry.id not in server_ministry_ids:
                raise serializers.ValidationError('El servidor no pertenece al ministerio seleccionado')
        return attrs

    def create(self, validatedData):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            validatedData['assignedBy'] = request.user
        return super().create(validatedData)


class AttendanceSerializer(serializers.ModelSerializer):
    serverData = serializers.SerializerMethodField()
    ministryData = serializers.SerializerMethodField()
    eventData = serializers.SerializerMethodField()

    class Meta:
        model = Attendance
        fields = ['id', 'server', 'serverData', 'event', 'eventData', 'ministry', 'ministryData',
                  'timestamp', 'integrityHash']
        read_only_fields = ['timestamp', 'integrityHash']

    def get_serverData(self, obj):
        return {'id': obj.server.id, 'firstName': obj.server.firstName, 'lastName': obj.server.lastName}

    def get_ministryData(self, obj):
        return {'id': obj.ministry.id, 'name': obj.ministry.name}

    def get_eventData(self, obj):
        return {'id': obj.event.id, 'name': obj.event.name}


class KioskoAuthSerializer(serializers.Serializer):
    pin = serializers.CharField(write_only=True)


class KioskoRegisterSerializer(serializers.Serializer):
    serverId = serializers.IntegerField()
    eventId = serializers.IntegerField()
    ministryId = serializers.IntegerField()


class ReconciliationSerializer(serializers.ModelSerializer):
    eventData = serializers.SerializerMethodField()
    details = serializers.SerializerMethodField()

    class Meta:
        model = Reconciliation
        fields = ['id', 'event', 'eventData', 'executedAt', 'executedBy', 'details']
        read_only_fields = ['executedAt', 'executedBy']

    def get_eventData(self, obj):
        return {'id': obj.event.id, 'name': obj.event.name}

    def get_details(self, obj):
        return ReconciliationDetailSerializer(obj.details.all(), many=True).data


class ReconciliationDetailSerializer(serializers.ModelSerializer):
    serverData = serializers.SerializerMethodField()
    replacedServerData = serializers.SerializerMethodField()

    class Meta:
        model = ReconciliationDetail
        fields = ['id', 'reconciliation', 'server', 'serverData', 'classification',
                  'replacedServer', 'replacedServerData']

    def get_serverData(self, obj):
        return {'id': obj.server.id, 'firstName': obj.server.firstName, 'lastName': obj.server.lastName}

    def get_replacedServerData(self, obj):
        if not obj.replacedServer:
            return None
        return {'id': obj.replacedServer.id, 'firstName': obj.replacedServer.firstName, 'lastName': obj.replacedServer.lastName}


class AuditLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditLog
        fields = '__all__'
        read_only_fields = ['previousHash', 'currentHash', 'timestamp']


class EventTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = EventType
        fields = '__all__'


class EventStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = EventStatus
        fields = '__all__'


class RecurringEventSerializer(serializers.ModelSerializer):
    eventTypeData = serializers.SerializerMethodField()
    statusData = serializers.SerializerMethodField()

    class Meta:
        model = RecurringEvent
        fields = ['id', 'name', 'weekday', 'startTime', 'endTime', 'eventType',
                  'eventTypeData', 'status', 'statusData', 'isActive']

    def get_eventTypeData(self, obj):
        return {'id': obj.eventType.id, 'name': obj.eventType.name}

    def get_statusData(self, obj):
        return {'id': obj.status.id, 'name': obj.status.name}

    def validate(self, attrs):
        startTime = attrs.get('startTime', self.instance.startTime if self.instance else None)
        endTime = attrs.get('endTime', self.instance.endTime if self.instance else None)
        if startTime >= endTime:
            raise serializers.ValidationError('La hora inicial debe ser menor que la hora final.')
        return attrs

    def create(self, validatedData):
        return RecurringEvent.objects.create(**validatedData)

    def update(self, instance, validatedData):
        for key, value in validatedData.items():
            setattr(instance, key, value)
        instance.save()
        return instance
