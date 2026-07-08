from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from events.models import (Event, EventType, EventStatus)
from events.serializers import (EventSerializer, EventTypeSerializer, EventStatusSerializer, RecurringEventSerializer)
from events.serializers import EventSerializer
from users.permissions import IsPastor
from django.shortcuts import render, get_object_or_404
from .models import (Event, EventType, EventStatus, RecurringEvent)
from ministries.models import Ministry
from django.http import JsonResponse
from rest_framework.response import Response
import json


class EventViewSet(viewsets.ModelViewSet):
    queryset = Event.objects.all()
    serializer_class = EventSerializer
    permission_classes = [IsAuthenticated, IsPastor]

    def get_queryset(self):
        queryset = Event.objects.select_related('type', 'status', 
                                                'leaderMinistry').prefetch_related('ministries')
        status = self.request.query_params.get('status')
        typeId = self.request.query_params.get('typeId')
        startDate = self.request.query_params.get('startDate')
        endDate = self.request.query_params.get('endDate')

        if status:
            queryset = queryset.filter(status__code=status)

        if typeId:
            queryset = queryset.filter(type_id=typeId)

        if startDate:
            queryset = queryset.filter(startDate__date__gte=startDate)

        if endDate:
            queryset = queryset.filter(endDate__date__lte=endDate)

        return queryset.order_by('-startDate')
    


class EventTypeViewSet(viewsets.ModelViewSet):
    queryset = EventType.objects.all()
    serializer_class = EventTypeSerializer

    permission_classes = [IsAuthenticated,IsPastor]

    def get_queryset(self):
        isActive = self.request.query_params.get('isActive')

        if isActive is None:
            return EventType.objects.all()

        return EventType.objects.filter(isActive=isActive == 'true')
    
    @action(detail=True, methods=['patch'])
    def deactivate(self, request, pk=None):
        print("Si entra")
        type = self.get_object()
        print(type)
        type.isActive = False

        type.save()

        return Response({
            "message": "Tipo desactivado"
        })


    @action(detail=True, methods=['patch'])
    def activate(self, request, pk=None):
        print("Si entra")
        type = self.get_object()
        print(type)
        type.isActive = True

        type.save()

        return Response({
            "message": "Tipo activado"
        })



class EventStatusViewSet(viewsets.ModelViewSet):
    queryset = EventStatus.objects.filter(isActive=True)
    serializer_class = EventStatusSerializer

    permission_classes = [IsAuthenticated, IsPastor]

    def get_queryset(self):
        isActive = self.request.query_params.get('isActive')

        if isActive is None:
            return EventStatus.objects.all()

        return EventStatus.objects.filter(isActive=isActive == 'true')
    
    @action(detail=True, methods=['patch'])
    def deactivate(self, request, pk=None):
        status = self.get_object()

        status.isActive = False

        status.save()

        return Response({
            "message": "Estado desactivado"
        })


    @action(detail=True, methods=['patch'])
    def activate(self, request, pk=None):
        status = self.get_object()

        status.isActive = True

        status.save()

        return Response({
            "message": "Estado activado"
        })



def eventsView(request):
    events = Event.objects.select_related('type', 'status', 'leaderMinistry', 'createdBy')
    typeId = request.GET.get('type')
    statusId = request.GET.get('status')
    startDate = request.GET.get('startDate')

    if typeId:
        events = events.filter(type_id=typeId)

    if statusId:
        events = events.filter(status_id=statusId)

    if startDate:
        events = events.filter(startDate__date=startDate)

    return render(request, 'events/index.html',
        {
            'events': events,
            'eventTypes': EventType.objects.all(),
            'eventStatuses': EventStatus.objects.all(),

            "eventsJson": EventSerializer(events, many=True).data,
            "eventTypesJson": EventTypeSerializer(
                EventType.objects.all(),
                many=True
            ).data,
            "eventStatusesJson": EventStatusSerializer(
                EventStatus.objects.all(),
                many=True
            ).data,
        }
    )


def createEventView(request):
    return render(request, 'events/create.html',
        {
            'eventTypes': EventType.objects.all(),
            'eventStatuses': EventStatus.objects.all(),
            'ministries': Ministry.objects.filter(isActive=True)
        }
    )


def detailEventView(request, eventId):
    event = get_object_or_404(Event.objects.prefetch_related('ministries')
                              .select_related(
                                    'type',
                                    'status',
                                    'leaderMinistry',
                                    'createdBy'
                                ), id=eventId)

    return render(request, 'events/detail.html',
        {
            'event': event
        }
    )



class RecurringEventViewSet(viewsets.ModelViewSet):

    queryset = RecurringEvent.objects.prefetch_related(
        'ministries'
    ).select_related(
        'eventType',
        'leaderMinistry',
        'status'
    )

    serializer_class = RecurringEventSerializer

    permission_classes = [
        IsAuthenticated,
        IsPastor
    ]



def eventTypesView(request):
    if request.method == 'POST':
        data = json.loads(request.body)

        typeId = data.get('id')

        if typeId:
            eventType = EventType.objects.get(id=typeId)

            eventType.name = data.get('name')

            eventType.save()
        else:
            EventType.objects.create(name=data.get("name"))

        return JsonResponse({
            "eventTypesJson": EventTypeSerializer(
                EventType.objects.all(),
                many=True
            ).data
        })

    return render(
        request,
        'events/types/index.html',
        {
            "eventTypesJson": EventTypeSerializer(
                EventType.objects.all(),
                many=True
            ).data
        }
    )


def eventStatusesView(request):
    if request.method == 'POST':
        data = json.loads(request.body)

        statusId = data.get('id')

        if statusId:
            eventStatus = EventStatus.objects.get(id=statusId)

            eventStatus.name = data.get('name')
            eventStatus.code = data.get('code')

            eventStatus.save()
        else:
            EventStatus.objects.create(name=data.get("name"),code=data.get("code"))

        return JsonResponse({
            "eventStatusJson": EventStatusSerializer(
                EventStatus.objects.all(),
                many=True
            ).data
        })

    return render(
        request,
        'events/status/index.html',
        {
            "eventStatusJson": EventStatusSerializer(
                EventStatus.objects.all(),
                many=True
            ).data
        }
    )


def recurringEventsView(request):

    editingRecurring = None

    editId = request.GET.get('edit')

    if editId:

        editingRecurring = RecurringEvent.objects.get(
            id=editId
        )

    if request.method == 'POST':

        recurringId = request.POST.get(
            'recurringId'
        )

        data = {
            'name': request.POST.get('name'),
            'weekday': request.POST.get('weekday'),
            'startTime': request.POST.get('startTime'),
            'endTime': request.POST.get('endTime')
        }

        if recurringId:

            recurring = RecurringEvent.objects.get(
                id=recurringId
            )

            recurring.name = data['name']
            recurring.weekday = data['weekday']
            recurring.startTime = data['startTime']
            recurring.endTime = data['endTime']

            recurring.save()

        else:

            RecurringEvent.objects.create(
                **data
            )

        editingRecurring = None

    return render(
        request,
        'events/recurring/index.html',
        {
            'recurringEvents': RecurringEvent.objects.all(),
            'editingRecurring': editingRecurring
        }
    )