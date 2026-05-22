from rest_framework import serializers
from events.models import (Event, EventMinistry, EventType, EventStatus)
from ministries.models import Ministry
from .models import RecurringEvent


class EventSerializer(serializers.ModelSerializer):
    ministryIds = serializers.ListField(child=serializers.IntegerField(), write_only=True)
    ministries = serializers.SerializerMethodField()
    typeData = serializers.SerializerMethodField()
    statusData = serializers.SerializerMethodField()
    leaderMinistryData = serializers.SerializerMethodField()


    class Meta:
        model = Event

        fields = ['id', 'name', 'type', 'typeData', 'status', 'statusData', 'startDate', 
                  'endDate', 'leaderMinistry', 'leaderMinistryData', 'ministries', 'ministryIds', 
                  'createdBy','createdAt']

        read_only_fields = ['createdBy', 'createdAt']


    def get_typeData(self, obj):
        return {
            'id': obj.type.id,
            'name': obj.type.name
        }


    def get_statusData(self, obj):
        return {
            'id': obj.status.id,
            'name': obj.status.name,
            'code': obj.status.code
        }


    def get_leaderMinistryData(self, obj):
        return {
            'id': obj.leaderMinistry.id,
            'name': obj.leaderMinistry.name
        }


    def get_ministries(self, obj):
        return [
            {
                'id': ministry.id,
                'name': ministry.name
            }
            for ministry in obj.ministries.all()
        ]


    def validate(self, attrs):
        startDate = attrs.get('startDate')
        endDate = attrs.get('endDate')
        ministryIds = attrs.get('ministryIds', [])
        leaderMinistry = attrs.get('leaderMinistry')

        if startDate >= endDate:
            raise serializers.ValidationError(
                'La fecha de inicio debe ser menor a la fecha final'
            )

        if len(ministryIds) == 0:
            raise serializers.ValidationError(
                'Debe seleccionar al menos un ministerio'
            )

        if leaderMinistry.id not in ministryIds:
            raise serializers.ValidationError(
                'El ministerio líder debe estar entre los participantes'
            )

        return attrs


    def create(self, validatedData):
        ministryIds = validatedData.pop('ministryIds', [])

        request = self.context.get('request')

        validatedData['createdBy'] = request.user

        event = Event.objects.create(**validatedData)

        self.assignMinistries(event, ministryIds)

        return event


    def update(self, instance, validatedData):
        ministryIds = validatedData.pop('ministryIds', None)

        for key, value in validatedData.items():
            setattr(instance, key, value)

        instance.save()

        if ministryIds is not None:
            EventMinistry.objects.filter(event=instance).delete()

            self.assignMinistries(instance, ministryIds)

        return instance


    def assignMinistries(self, event, ministryIds):
        ministries = Ministry.objects.filter(id__in=ministryIds, isActive=True)

        for ministry in ministries:
            EventMinistry.objects.create(event=event,ministry=ministry)



class EventTypeSerializer(serializers.ModelSerializer):

    class Meta:

        model = EventType

        fields = '__all__'



class EventStatusSerializer(serializers.ModelSerializer):

    class Meta:

        model = EventStatus

        fields = '__all__'



class RecurringEventSerializer(serializers.ModelSerializer):
    ministryIds = serializers.ListField(child=serializers.IntegerField(), write_only=True)
    ministries = serializers.SerializerMethodField()

    class Meta:
        model = RecurringEvent

        fields = ['id', 'name', 'weekday', 'startTime', 'endTime', 'eventType', 'leaderMinistry',
                  'status', 'isActive', 'ministries', 'ministryIds']

    def get_ministries(self, obj):
        return [
            {
                'id': ministry.id,
                'name': ministry.name
            }
            for ministry in obj.ministries.all()
        ]

    def validate(self, attrs):
        if attrs['startTime'] >= attrs['endTime']:
            raise serializers.ValidationError('La hora inicial debe ser menor')

        if len(attrs['ministryIds']) == 0:
            raise serializers.ValidationError('Debe seleccionar ministerios')

        return attrs

    def create(self, validatedData):
        ministryIds = validatedData.pop('ministryIds', [])

        recurring = RecurringEvent.objects.create(**validatedData)

        ministries = Ministry.objects.filter(id__in=ministryIds)

        recurring.ministries.set(ministries)

        return recurring

    def update(self, instance, validatedData):
        ministryIds = validatedData.pop('ministryIds', None)

        for key, value in validatedData.items():
            setattr(instance, key, value)

        instance.save()

        if ministryIds is not None:
            ministries = Ministry.objects.filter(id__in=ministryIds)

            instance.ministries.set(ministries)

        return instance