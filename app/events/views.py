from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.utils import timezone
from django.contrib.auth.hashers import check_password
from django.db.models import Count, Q
from datetime import timedelta, datetime
import json

from .models import (Event, EventType, EventStatus, RecurringEvent, Assignment, EventMinistry,
                     Attendance, KioskoAttempt, Reconciliation, ReconciliationDetail, AuditLog)
from .serializers import (EventSerializer, EventTypeSerializer, EventStatusSerializer,
                          RecurringEventSerializer, AssignmentSerializer, AttendanceSerializer,
                          ReconciliationSerializer, ReconciliationDetailSerializer,
                           AuditLogSerializer, KioskoAuthSerializer, KioskoRegisterSerializer,
                           KioskoCheckoutSerializer)
from ministries.models import Ministry
from ministries.serializers import MinistrySerializer
from servers.models import Server
from servers.serializers import ServerSerializer
from users.permissions import IsPastor, IsPastorOrReadOnly


class EventViewSet(viewsets.ModelViewSet):
    queryset = Event.objects.all()
    serializer_class = EventSerializer
    permission_classes = [IsAuthenticated, IsPastorOrReadOnly]

    def get_queryset(self):
        queryset = Event.objects.select_related('type', 'status', 'leaderMinistry').prefetch_related('ministries')
        user = self.request.user
        status_filter = self.request.query_params.get('status')
        typeId = self.request.query_params.get('typeId')
        startDate = self.request.query_params.get('startDate')
        endDate = self.request.query_params.get('endDate')

        if status_filter:
            queryset = queryset.filter(status__id=status_filter)
        if typeId:
            queryset = queryset.filter(type_id=typeId)
        if startDate:
            queryset = queryset.filter(startDate__date=startDate)

        queryset = queryset.order_by('-startDate')

        if user.role == 'LIDER':
            my_ministry = Ministry.objects.filter(leaderAssigned=user).first()
            if my_ministry:
                own_events = list(queryset.filter(leaderMinistry=my_ministry))
                other_events = list(queryset.exclude(leaderMinistry=my_ministry))
                return own_events + other_events
            else:
                return Event.objects.none()

        return queryset

    def perform_create(self, serializer):
        serializer.save(createdBy=self.request.user)

    def update(self, request, *args, **kwargs):
        event = self.get_object()
        user = request.user
        if user.role == 'LIDER':
            my_ministry = Ministry.objects.filter(leaderAssigned=user).first()
            if my_ministry and event.leaderMinistry_id != my_ministry.id:
                return Response({'error': 'No tienes permisos para modificar este evento'}, status=status.HTTP_403_FORBIDDEN)
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        event = self.get_object()
        user = request.user
        if user.role == 'LIDER':
            my_ministry = Ministry.objects.filter(leaderAssigned=user).first()
            if my_ministry and event.leaderMinistry_id != my_ministry.id:
                return Response({'error': 'No tienes permisos para modificar este evento'}, status=status.HTTP_403_FORBIDDEN)
        return super().partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        event = self.get_object()
        user = request.user
        if user.role == 'LIDER':
            my_ministry = Ministry.objects.filter(leaderAssigned=user).first()
            if my_ministry and event.leaderMinistry_id != my_ministry.id:
                return Response({'error': 'No tienes permisos para eliminar este evento'}, status=status.HTTP_403_FORBIDDEN)
        return super().destroy(request, *args, **kwargs)

    @action(detail=True, methods=['patch'])
    def finalize(self, request, pk=None):
        event = self.get_object()
        user = request.user

        if user.role == 'LIDER':
            my_ministry = Ministry.objects.filter(leaderAssigned=user).first()
            if my_ministry and event.leaderMinistry_id != my_ministry.id:
                return Response({'error': 'No tienes permisos para finalizar este evento'}, status=status.HTTP_403_FORBIDDEN)

        if event.status.code == 'RECONCILIADO':
            return Response({'error': 'No se puede finalizar un evento ya reconciliado'}, status=status.HTTP_400_BAD_REQUEST)
        if event.status.code == 'FINALIZADO':
            return Response({'error': 'El evento ya está finalizado'}, status=status.HTTP_400_BAD_REQUEST)
        if event.status.code == 'CANCELADO':
            return Response({'error': 'No se puede finalizar un evento cancelado'}, status=status.HTTP_400_BAD_REQUEST)

        event.status = EventStatus.objects.get(code='FINALIZADO')
        event.save(update_fields=['status'])
        return Response({'message': 'Evento finalizado exitosamente'})

    @action(detail=True, methods=['patch'])
    def cancel(self, request, pk=None):
        return self.deactivate(request, pk)

    @action(detail=True, methods=['patch'])
    def deactivate(self, request, pk=None):
        event = self.get_object()
        user = request.user

        if user.role == 'LIDER':
            my_ministry = Ministry.objects.filter(leaderAssigned=user).first()
            if my_ministry and event.leaderMinistry_id != my_ministry.id:
                return Response({'error': 'No tienes permisos para cancelar este evento'}, status=status.HTTP_403_FORBIDDEN)

        if event.status.code in ('FINALIZADO', 'RECONCILIADO', 'CANCELADO'):
            return Response({'error': 'El evento ya está finalizado, reconciliado o cancelado'}, status=status.HTTP_400_BAD_REQUEST)

        event.status = EventStatus.objects.get(code='CANCELADO')
        event.save()
        return Response({'message': 'Evento cancelado exitosamente'})

    @action(detail=True, methods=['get', 'post', 'delete'])
    def assignments(self, request, pk=None):
        event = self.get_object()

        if request.method == 'GET':
            qs = Assignment.objects.filter(event=event).select_related('server', 'ministry')
            return Response(AssignmentSerializer(qs, many=True).data)

        if request.method in ('POST', 'DELETE'):
            if event.status.code in ('FINALIZADO', 'RECONCILIADO', 'CANCELADO'):
                return Response({'error': 'No se pueden modificar asignaciones en eventos finalizados, reconciliados o cancelados'},
                                status=status.HTTP_400_BAD_REQUEST)

            user = request.user
            if user.role == 'LIDER':
                my_ministry = Ministry.objects.filter(leaderAssigned=user).first()
                if my_ministry and event.leaderMinistry_id != my_ministry.id:
                    return Response({'error': 'No tienes permisos para modificar asignaciones de este evento'},
                                    status=status.HTTP_403_FORBIDDEN)

            if request.method == 'POST':
                if user.role == 'LIDER':
                    my_ministry = Ministry.objects.filter(leaderAssigned=user).first()
                    server_id = request.data.get('server')
                    if server_id and my_ministry:
                        server = Server.objects.filter(id=server_id).first()
                        if server and not server.ministries.filter(id=my_ministry.id).exists():
                            return Response({'error': 'Solo puedes asignar servidores de tu ministerio'},
                                            status=status.HTTP_403_FORBIDDEN)

                serializer = AssignmentSerializer(data={'event': event.id, **request.data}, context={'request': request})
                serializer.is_valid(raise_exception=True)
                serializer.save()
                return Response(serializer.data, status=status.HTTP_201_CREATED)

            if request.method == 'DELETE':
                assignment_id = request.query_params.get('assignmentId')
                if not assignment_id:
                    return Response({'error': 'Se requiere assignmentId'}, status=status.HTTP_400_BAD_REQUEST)
                assignment = get_object_or_404(Assignment, id=assignment_id, event=event)
                assignment.delete()
                return Response({'message': 'Asignación eliminada'})

    @action(detail=True, methods=['get', 'post', 'patch'])
    def reconcile(self, request, pk=None):
        event = self.get_object()
        user = request.user

        if user.role == 'LIDER':
            my_ministry = Ministry.objects.filter(leaderAssigned=user).first()
            if my_ministry and event.leaderMinistry_id != my_ministry.id:
                return Response({'error': 'No tienes permisos para reconciliar este evento'}, status=status.HTTP_403_FORBIDDEN)

        if event.status.code not in ('FINALIZADO', 'RECONCILIADO'):
            return Response({'error': 'Solo se puede reconciliar eventos finalizados o reconciliados'}, status=status.HTTP_400_BAD_REQUEST)

        if request.method == 'PATCH':
            old_reconciliation = Reconciliation.objects.filter(event=event).first()
            if old_reconciliation:
                old_reconciliation.delete()
            event.status = EventStatus.objects.get(code='FINALIZADO')
            event.save(update_fields=['status'])
            return Response({'message': 'Reconciliación eliminada, puede reconciliar de nuevo'})

        if Reconciliation.objects.filter(event=event).exists():
            return Response({'error': 'El evento ya fue reconciliado'}, status=status.HTTP_400_BAD_REQUEST)

        if request.method == 'GET':
            assignments = Assignment.objects.filter(event=event).select_related('server', 'ministry')
            attendances = Attendance.objects.filter(event=event).select_related('server')

            attendance_map = {a.server_id: a for a in attendances}
            assigned_ids = set(a.server_id for a in assignments)
            attended_ids = set(attendance_map.keys())
            volunteer_ids = attended_ids - assigned_ids

            preview = []
            for a in assignments:
                att = attendance_map.get(a.server_id)
                if att is not None and att.checkOutTime is not None:
                    classification = 'ASSIGNED'
                elif att is not None:
                    classification = 'INCOMPLETE'
                else:
                    classification = 'ABSENT'
                preview.append({
                    'serverId': a.server.id,
                    'serverName': f'{a.server.firstName} {a.server.lastName}',
                    'ministry': a.ministry.name,
                    'classification': classification,
                })

            for a in attendances.filter(server_id__in=volunteer_ids):
                classification = 'VOLUNTEER' if a.checkOutTime is not None else 'INCOMPLETE'
                preview.append({
                    'serverId': a.server.id,
                    'serverName': f'{a.server.firstName} {a.server.lastName}',
                    'ministry': a.ministry.name,
                    'classification': classification,
                })

            return Response(preview)

        if request.method == 'POST':
            assignments = Assignment.objects.filter(event=event).select_related('server', 'ministry')
            attendances = Attendance.objects.filter(event=event).select_related('server')

            attendance_map = {a.server_id: a for a in attendances}
            assigned_ids = set(a.server_id for a in assignments)
            attended_ids = set(attendance_map.keys())
            volunteer_ids = attended_ids - assigned_ids

            reconciliation = Reconciliation.objects.create(event=event, executedBy=request.user)

            for a in assignments:
                att = attendance_map.get(a.server_id)
                if att is not None and att.checkOutTime is not None:
                    classification = 'ASSIGNED'
                elif att is not None:
                    classification = 'INCOMPLETE'
                else:
                    classification = 'ABSENT'
                ReconciliationDetail.objects.create(
                    reconciliation=reconciliation,
                    server=a.server,
                    classification=classification,
                )

            for a in attendances.filter(server_id__in=volunteer_ids):
                classification = 'VOLUNTEER' if a.checkOutTime is not None else 'INCOMPLETE'
                ReconciliationDetail.objects.create(
                    reconciliation=reconciliation,
                    server=a.server,
                    classification=classification,
                )

            event.status = EventStatus.objects.get(code='RECONCILIADO')
            event.save(update_fields=['status'])

            AuditLog.objects.create(
                action='RECONCILIATION_EXECUTED',
                table='Reconciliation',
                recordId=reconciliation.id,
                performedBy=str(request.user),
                details={'eventId': event.id, 'eventName': event.name},
            )

            return Response({'message': 'Reconciliación ejecutada exitosamente', 'id': reconciliation.id})


class EventTypeViewSet(viewsets.ModelViewSet):
    queryset = EventType.objects.all()
    serializer_class = EventTypeSerializer
    permission_classes = [IsAuthenticated, IsPastorOrReadOnly]

    def get_queryset(self):
        isActive = self.request.query_params.get('isActive')
        if isActive is None:
            return EventType.objects.all()
        return EventType.objects.filter(isActive=isActive == 'true')

    @action(detail=True, methods=['patch'])
    def deactivate(self, request, pk=None):
        obj = self.get_object()
        obj.isActive = False
        obj.save()
        return Response({"message": "Tipo desactivado"})

    @action(detail=True, methods=['patch'])
    def activate(self, request, pk=None):
        obj = self.get_object()
        obj.isActive = True
        obj.save()
        return Response({"message": "Tipo activado"})


class EventStatusViewSet(viewsets.ModelViewSet):
    queryset = EventStatus.objects.filter(isActive=True)
    serializer_class = EventStatusSerializer
    permission_classes = [IsAuthenticated]


    def get_queryset(self):
        isActive = self.request.query_params.get('isActive')
        if isActive is None:
            return EventStatus.objects.all()
        return EventStatus.objects.filter(isActive=isActive == 'true')
    @action(detail=True, methods=['patch'])
    def deactivate(self, request, pk=None):
        obj = self.get_object()
        obj.isActive = False
        obj.save()
        return Response({"message": "Estado desactivado"})

    @action(detail=True, methods=['patch'])
    def activate(self, request, pk=None):
        obj = self.get_object()
        obj.isActive = True
        obj.save()
        return Response({"message": "Estado activado"})


class AssignmentViewSet(viewsets.ModelViewSet):
    queryset = Assignment.objects.all()
    serializer_class = AssignmentSerializer
    permission_classes = [IsAuthenticated, IsPastorOrReadOnly]

    def get_queryset(self):
        qs = Assignment.objects.select_related('server', 'ministry', 'event')
        event_id = self.request.query_params.get('event')
        if event_id:
            qs = qs.filter(event_id=event_id)
        return qs

    def perform_create(self, serializer):
        serializer.save(assignedBy=self.request.user)


class AttendanceViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Attendance.objects.all()
    serializer_class = AttendanceSerializer
    permission_classes = [IsAuthenticated, IsPastor]

    def get_queryset(self):
        qs = Attendance.objects.select_related('server', 'event', 'ministry')
        event_id = self.request.query_params.get('event')
        server_id = self.request.query_params.get('server')
        if event_id:
            qs = qs.filter(event_id=event_id)
        if server_id:
            qs = qs.filter(server_id=server_id)
        return qs.order_by('-timestamp')


class ReconciliationViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Reconciliation.objects.all()
    serializer_class = ReconciliationSerializer
    permission_classes = [IsAuthenticated, IsPastor]

    def get_queryset(self):
        qs = Reconciliation.objects.select_related('event', 'executedBy').prefetch_related('details__server')
        event_id = self.request.query_params.get('event')
        if event_id:
            qs = qs.filter(event_id=event_id)
        return qs.order_by('-executedAt')

    @action(detail=True, methods=['patch'], url_path='details/(?P<server_id>[^/.]+)')
    def mark_replacement(self, request, pk=None, server_id=None):
        reconciliation = self.get_object()

        if reconciliation.event.status.code != 'RECONCILIADO':
            return Response({'error': 'Solo se puede modificar una reconciliación ya ejecutada'}, status=status.HTTP_400_BAD_REQUEST)

        replaced_server_id = request.data.get('replacedServerId')
        if not replaced_server_id:
            return Response({'error': 'Se requiere replacedServerId'}, status=status.HTTP_400_BAD_REQUEST)

        if int(server_id) == int(replaced_server_id):
            return Response({'error': 'Un servidor no puede reemplazarse a sí mismo'}, status=status.HTTP_400_BAD_REQUEST)

        detail = get_object_or_404(ReconciliationDetail, reconciliation=reconciliation, server_id=server_id)
        replaced_detail = get_object_or_404(ReconciliationDetail, reconciliation=reconciliation, server_id=replaced_server_id)

        if replaced_detail.classification != 'ASSIGNED':
            return Response({'error': 'El servidor reemplazado debe haber estado asignado (ASSIGNED)'}, status=status.HTTP_400_BAD_REQUEST)

        detail.classification = 'REPLACEMENT'
        detail.replacedServer_id = replaced_server_id
        detail.save()

        replaced_detail.classification = 'ABSENT'
        replaced_detail.save()

        AuditLog.objects.create(
            action='RECONCILIATION_REPLACEMENT',
            table='ReconciliationDetail',
            recordId=detail.id,
            performedBy=str(request.user),
            details={'reconciliationId': reconciliation.id, 'replacedById': server_id, 'replacedId': replaced_server_id},
        )

        return Response({'message': 'Reemplazo registrado exitosamente'})


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AuditLog.objects.all()
    serializer_class = AuditLogSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = AuditLog.objects.all()
        user = self.request.user
        action = self.request.query_params.get('action')

        if user.role == 'LIDER':
            from ministries.models import Ministry
            my_ministry = Ministry.objects.filter(leaderAssigned=user).first()
            if my_ministry:
                server_ids = list(my_ministry.servers.values_list('id', flat=True))
                qs = qs.filter(
                    Q(details__serverId__in=server_ids) |
                    Q(performedBy__startswith='server:') & Q(details__serverId__in=server_ids)
                ).distinct()
            else:
                qs = AuditLog.objects.none()

        if action:
            qs = qs.filter(action=action)
        return qs[:100]

    @action(detail=False, methods=['get'])
    def verify(self, request):
        import hashlib
        logs = AuditLog.objects.order_by('id')
        results = []
        valid = True
        prev_hash = '0' * 64

        for log in logs:
            expected_prev = prev_hash
            prev_hash_ok = log.previousHash == expected_prev
            ts = log.timestamp.replace(microsecond=0).isoformat() if log.timestamp else ''
            raw = f'{log.action}:{log.table}:{log.recordId}:{log.previousHash}:{ts}'
            expected_hash = hashlib.sha256(raw.encode()).hexdigest()
            hash_ok = log.currentHash == expected_hash
            if not (prev_hash_ok and hash_ok):
                valid = False
            results.append({
                'id': log.id,
                'action': log.action,
                'previousHashOk': prev_hash_ok,
                'hashOk': hash_ok,
            })
            prev_hash = log.currentHash

        return Response({
            'valid': valid,
            'totalLogs': len(results),
            'details': results,
        })


class RecurringEventViewSet(viewsets.ModelViewSet):
    queryset = RecurringEvent.objects.filter(isActive=True)
    serializer_class = RecurringEventSerializer
    permission_classes = [IsAuthenticated, IsPastor]

    def get_queryset(self):
        isActive = self.request.query_params.get('isActive')
        if isActive is None:
            return RecurringEvent.objects.all()
        return RecurringEvent.objects.filter(isActive=isActive == 'true')

    @action(detail=True, methods=['patch'])
    def deactivate(self, request, pk=None):
        obj = self.get_object()
        obj.isActive = False
        obj.save()
        return Response({"message": "Evento Recurrente desactivado"})

    @action(detail=True, methods=['patch'])
    def activate(self, request, pk=None):
        obj = self.get_object()
        obj.isActive = True
        obj.save()
        return Response({"message": "Evento Recurrente activado"})


# ─── KIOSKO ─────────────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([AllowAny])
def kiosko_auth(request):
    serializer = KioskoAuthSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    pin = serializer.validated_data['pin']
    server = None

    for s in Server.objects.filter(isActive=True):
        if check_password(pin, s.pin):
            server = s
            break

    ip = request.META.get('REMOTE_ADDR')

    if not server:
        KioskoAttempt.objects.create(server_id=0, ipAddress=ip, successful=False)
        return Response({'error': 'PIN incorrecto'}, status=status.HTTP_401_UNAUTHORIZED)

    KioskoAttempt.objects.create(server=server, ipAddress=ip, successful=True)

    ministries = [
        {'id': m.id, 'name': m.name}
        for m in server.ministries.filter(isActive=True)
    ]

    return Response({
        'serverId': server.id,
        'firstName': server.firstName,
        'lastName': server.lastName,
        'ministries': ministries,
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def kiosko_active_events(request):
    server_id = request.query_params.get('serverId')
    if not server_id:
        return Response({'error': 'Se requiere serverId'}, status=status.HTTP_400_BAD_REQUEST)

    now = timezone.now()
    buffer = timedelta(minutes=30)
    events = Event.objects.filter(
        status__code='ACTIVO',
        startDate__lte=now + buffer,
        endDate__gte=now - buffer,
    ).select_related('type', 'status').prefetch_related('ministries')

    server = get_object_or_404(Server, id=server_id)
    server_ministry_ids = set(server.ministries.values_list('id', flat=True))

    result = []
    for event in events:
        event_ministry_ids = set(event.ministries.values_list('id', flat=True))

        if event.type.name == 'ORACION':
            participant_ministries = list(event.ministries.all().values('id', 'name'))
        else:
            participant_ministries = [
                {'id': m.id, 'name': m.name}
                for m in event.ministries.all()
                if m.id in server_ministry_ids
            ]
            if not participant_ministries:
                continue

        attendance = Attendance.objects.filter(server_id=server_id, event=event).first()

        can_checkout = False
        if attendance and attendance.checkOutTime is None:
            elapsed = now - attendance.timestamp
            duration = event.endDate - event.startDate
            if duration.total_seconds() > 0:
                can_checkout = elapsed >= duration * 0.7

        result.append({
            'eventId': event.id,
            'name': event.name,
            'type': event.type.name,
            'participantMinistries': participant_ministries,
            'alreadyRegistered': attendance is not None,
            'alreadyCheckedOut': attendance.checkOutTime is not None if attendance else False,
            'attendanceId': attendance.id if attendance else None,
            'canCheckout': can_checkout,
        })

    return Response(result)


@api_view(['POST'])
@permission_classes([AllowAny])
def kiosko_register(request):
    serializer = KioskoRegisterSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    server_id = serializer.validated_data['serverId']
    event_id = serializer.validated_data['eventId']
    ministry_id = serializer.validated_data['ministryId']

    event = get_object_or_404(Event, id=event_id)
    server = get_object_or_404(Server, id=server_id)

    if event.status.code != 'ACTIVO':
        return Response({'error': 'El evento no está activo'}, status=status.HTTP_400_BAD_REQUEST)

    if Attendance.objects.filter(server=server, event=event).exists():
        return Response({'error': 'Ya tienes registrada tu asistencia a este evento'}, status=status.HTTP_400_BAD_REQUEST)

    attendance = Attendance.objects.create(
        server=server,
        event=event,
        ministry_id=ministry_id,
    )

    AuditLog.objects.create(
        action='ATTENDANCE_REGISTERED',
        table='Attendance',
        recordId=attendance.id,
        performedBy=f'server:{server.id}',
        details={'eventId': event.id, 'serverId': server.id, 'ministryId': ministry_id},
    )

    return Response({
        'message': 'Asistencia registrada exitosamente',
        'serverName': f'{server.firstName} {server.lastName}',
        'eventName': event.name,
        'timestamp': attendance.timestamp.isoformat(),
    })


@api_view(['POST'])
@permission_classes([AllowAny])
def kiosko_checkout(request):
    serializer = KioskoCheckoutSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    server_id = serializer.validated_data['serverId']
    event_id = serializer.validated_data['eventId']

    event = get_object_or_404(Event, id=event_id)
    server = get_object_or_404(Server, id=server_id)

    if event.status.code not in ('ACTIVO', 'PROGRAMADO'):
        return Response({'error': 'El evento no está activo'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        attendance = Attendance.objects.get(server=server, event=event)
    except Attendance.DoesNotExist:
        return Response({'error': 'No tienes registro de ingreso a este evento'}, status=status.HTTP_400_BAD_REQUEST)

    if attendance.checkOutTime is not None:
        return Response({'error': 'Ya registraste tu salida de este evento'}, status=status.HTTP_400_BAD_REQUEST)

    duration = event.endDate - event.startDate
    if duration.total_seconds() > 0:
        elapsed = timezone.now() - attendance.timestamp
        if elapsed < duration * 0.7:
            remaining = (duration * 0.7) - elapsed
            minutes = int(remaining.total_seconds() // 60) + 1
            return Response({
                'error': f'Debe esperar aproximadamente {minutes} minuto(s) más para registrar su salida'
            }, status=status.HTTP_400_BAD_REQUEST)

    attendance.checkOutTime = timezone.now()
    attendance.save()

    AuditLog.objects.create(
        action='ATTENDANCE_REGISTERED',
        table='Attendance',
        recordId=attendance.id,
        performedBy=f'server:{server.id}',
        details={'eventId': event.id, 'serverId': server.id, 'action': 'checkout'},
    )

    return Response({
        'message': 'Salida registrada exitosamente',
        'serverName': f'{server.firstName} {server.lastName}',
        'eventName': event.name,
        'checkOutTime': attendance.checkOutTime.isoformat(),
    })


# ─── REPORTES ────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def report_server_attendance(request, server_id):
    server = get_object_or_404(Server, id=server_id)
    start_date = request.query_params.get('startDate')
    end_date = request.query_params.get('endDate')
    ministry_id = request.query_params.get('ministryId')

    reconciliations = Reconciliation.objects.filter(
        details__server=server,
        event__status__code='RECONCILIADO',
    ).distinct().select_related('event')

    if start_date:
        reconciliations = reconciliations.filter(event__startDate__date__gte=start_date)
    if end_date:
        reconciliations = reconciliations.filter(event__endDate__date__lte=end_date)

    event_ids = [r.event_id for r in reconciliations]
    attendances = Attendance.objects.filter(server=server, event_id__in=event_ids)
    attendance_map = {a.event_id: a for a in attendances}

    total_assigned = 0
    total_attended = 0
    total_absent = 0
    total_incomplete = 0
    total_volunteer = 0
    total_replacement = 0
    history = []

    for r in reconciliations:
        detail = r.details.filter(server=server).first()
        if not detail:
            continue

        if detail.classification == 'ASSIGNED':
            total_assigned += 1
            total_attended += 1
        elif detail.classification == 'INCOMPLETE':
            total_incomplete += 1
        elif detail.classification == 'ABSENT':
            total_absent += 1
        elif detail.classification == 'VOLUNTEER':
            total_volunteer += 1
        elif detail.classification == 'REPLACEMENT':
            total_replacement += 1
            total_attended += 1

        att = attendance_map.get(r.event.id)
        history.append({
            'eventId': r.event.id,
            'eventName': r.event.name,
            'eventDate': r.event.startDate,
            'classification': detail.classification,
            'checkIn': att.timestamp if att else None,
            'checkOut': att.checkOutTime if att else None,
        })

    total_assignments = total_assigned + total_incomplete + total_absent
    attendance_rate = round((total_attended / total_assignments * 100), 1) if total_assignments > 0 else 0

    return Response({
        'serverId': server.id,
        'serverName': f'{server.firstName} {server.lastName}',
        'totalEvents': len(history),
        'totalAssigned': total_assigned,
        'totalAttended': total_attended,
        'totalIncomplete': total_incomplete,
        'totalAbsent': total_absent,
        'totalVolunteer': total_volunteer,
        'totalReplacements': total_replacement,
        'attendanceRate': attendance_rate,
        'history': history,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def report_ministry_indicators(request, ministry_id):
    ministry = get_object_or_404(Ministry, id=ministry_id)
    start_date = request.query_params.get('startDate')
    end_date = request.query_params.get('endDate')

    events = Event.objects.filter(ministries=ministry, status__code='RECONCILIADO')
    if start_date:
        events = events.filter(startDate__date__gte=start_date)
    if end_date:
        events = events.filter(endDate__date__lte=end_date)

    total_events = events.count()
    reconciliations = Reconciliation.objects.filter(event__in=events).prefetch_related('details__server')

    server_stats = {}
    for r in reconciliations:
        for d in r.details.all():
            sid = d.server_id
            if sid not in server_stats:
                server_stats[sid] = {
                    'serverId': sid,
                    'serverName': f'{d.server.firstName} {d.server.lastName}',
                    'total': 0,
                    'attended': 0,
                    'absent': 0,
                    'incomplete': 0,
                }
            server_stats[sid]['total'] += 1
            if d.classification in ('ASSIGNED', 'REPLACEMENT'):
                server_stats[sid]['attended'] += 1
            elif d.classification == 'ABSENT':
                server_stats[sid]['absent'] += 1
            elif d.classification == 'INCOMPLETE':
                server_stats[sid]['incomplete'] += 1

    sorted_servers = sorted(server_stats.values(), key=lambda x: x['attended'], reverse=True)
    most_active = sorted_servers[:5] if sorted_servers else []
    frequent_absent = [s for s in sorted_servers if s['total'] > 0 and (s['absent'] / s['total']) > 0.5][:5]

    total_attendance = sum(s['attended'] for s in server_stats.values())
    total_assignments = sum(s['total'] for s in server_stats.values())
    avg_attendance = round((total_attendance / total_assignments * 100), 1) if total_assignments > 0 else 0

    return Response({
        'ministryId': ministry.id,
        'ministryName': ministry.name,
        'totalEvents': total_events,
        'totalServers': len(server_stats),
        'attendanceRate': avg_attendance,
        'mostActiveServers': most_active,
        'frequentAbsentServers': frequent_absent,
        'serverStats': sorted_servers,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def report_general(request):
    start_date = request.query_params.get('startDate')
    end_date = request.query_params.get('endDate')
    user = request.user

    if user.role == 'LIDER':
        my_ministry = Ministry.objects.filter(leaderAssigned=user).first()
        if not my_ministry:
            return Response({'ministries': [], 'totalMinistries': 0})
        ministries = Ministry.objects.filter(id=my_ministry.id, isActive=True)
    else:
        ministries = Ministry.objects.filter(isActive=True)

    result = []

    for ministry in ministries:
        events = Event.objects.filter(ministries=ministry, status__code='RECONCILIADO')
        if start_date:
            events = events.filter(startDate__date__gte=start_date)
        if end_date:
            events = events.filter(endDate__date__lte=end_date)

        total_events = events.count()
        reconciliations = Reconciliation.objects.filter(event__in=events).prefetch_related('details')

        total_assigned = 0
        total_attended = 0
        total_incomplete = 0
        servers_set = set()

        for r in reconciliations:
            for d in r.details.all():
                servers_set.add(d.server_id)
                if d.classification == 'INCOMPLETE':
                    total_incomplete += 1
                else:
                    total_assigned += 1
                if d.classification in ('ASSIGNED', 'REPLACEMENT'):
                    total_attended += 1

        rate = round((total_attended / total_assigned * 100), 1) if total_assigned > 0 else 0

        result.append({
            'ministryId': ministry.id,
            'ministryName': ministry.name,
            'totalEvents': total_events,
            'totalServers': len(servers_set),
            'attendanceRate': rate,
        })

    return Response({'ministries': result, 'totalMinistries': len(result)})


# ─── VISTAS HTML ─────────────────────────────────────────────────

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

    return render(request, 'events/index.html', {
        'events': events,
        'eventTypes': EventType.objects.all(),
        'eventStatuses': EventStatus.objects.all(),
        'eventsJson': EventSerializer(events, many=True).data,
        'eventTypesJson': EventTypeSerializer(EventType.objects.all(), many=True).data,
        'eventStatusesJson': EventStatusSerializer(EventStatus.objects.all(), many=True).data,
        'ministriesJson': MinistrySerializer(Ministry.objects.filter(isActive=True), many=True).data,
    })


def eventFormView(request):
    event_id = request.GET.get('edit')
    event = None
    eventJson = None
    if event_id:
        event = get_object_or_404(Event.objects.prefetch_related('ministries', 'assignments__server', 'assignments__ministry')
                                  .select_related('type', 'status', 'leaderMinistry'), id=event_id)
        eventJson = EventSerializer(event).data

    user = request.user
    userMinistryId = None
    userRole = None
    if user.is_authenticated:
        my_ministry = Ministry.objects.filter(leaderAssigned=user).first()
        userMinistryId = my_ministry.id if my_ministry else None
        userRole = user.role

    return render(request, 'events/form.html', {
        'eventTypesJson': EventTypeSerializer(EventType.objects.all(), many=True).data,
        'eventStatusesJson': EventStatusSerializer(EventStatus.objects.all(), many=True).data,
        'ministriesJson': MinistrySerializer(Ministry.objects.filter(isActive=True), many=True).data,
        'eventJson': eventJson,
        'userMinistryId': userMinistryId,
        'userRole': userRole,
    })


def detailEventView(request, eventId):
    event = get_object_or_404(Event.objects.prefetch_related('ministries', 'assignments__server', 'assignments__ministry')
                              .select_related('type', 'status', 'leaderMinistry', 'createdBy'), id=eventId)

    ministries = Ministry.objects.filter(isActive=True)
    assignments = Assignment.objects.filter(event=event).select_related('server', 'ministry')
    attendances = Attendance.objects.filter(event=event).select_related('server', 'ministry')
    reconciliation = Reconciliation.objects.filter(event=event).last()

    return render(request, 'events/detail.html', {
        'event': event,
        'eventJson': EventSerializer(event).data,
        'assignmentsJson': AssignmentSerializer(assignments, many=True).data,
        'ministriesJson': MinistrySerializer(ministries, many=True).data,
        'attendancesJson': AttendanceSerializer(attendances, many=True).data,
        'reconciliationJson': ReconciliationSerializer(reconciliation).data if reconciliation else None,
    })


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
        return JsonResponse({"eventTypesJson": EventTypeSerializer(EventType.objects.all(), many=True).data})

    return render(request, 'events/types/index.html', {
        "eventTypesJson": EventTypeSerializer(EventType.objects.all(), many=True).data
    })


def eventStatusesView(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        statusId = data.get('id')
        if statusId:
            eventStatus = EventStatus.objects.get(id=statusId)
            eventStatus.name = data.get('name')
            eventStatus.save()
        else:
            EventStatus.objects.create(name=data.get("name"))
        return JsonResponse({"eventStatusJson": EventStatusSerializer(EventStatus.objects.all(), many=True).data})

    return render(request, 'events/status/index.html', {
        "eventStatusJson": EventStatusSerializer(EventStatus.objects.all(), many=True).data
    })


def recurringEventsView(request):
    editingRecurring = None
    editId = request.GET.get('edit')
    if editId:
        editingRecurring = RecurringEvent.objects.get(id=editId)

    if request.method == 'POST':
        recurringId = request.POST.get('recurringId')
        data = {
            'name': request.POST.get('name'),
            'weekday': request.POST.get('weekday'),
            'startTime': request.POST.get('startTime'),
            'endTime': request.POST.get('endTime'),
        }
        if recurringId:
            recurring = RecurringEvent.objects.get(id=recurringId)
            for key, value in data.items():
                setattr(recurring, key, value)
            recurring.save()
        else:
            RecurringEvent.objects.create(**data)
        editingRecurring = None

    return render(request, 'events/recurring/index.html', {
        'recurringEvents': RecurringEvent.objects.all(),
        'recurringEventsJson': RecurringEventSerializer(RecurringEvent.objects.all(), many=True).data,
        'eventTypesJson': EventTypeSerializer(EventType.objects.all(), many=True).data,
        'editingRecurring': editingRecurring,
    })


def events_reports_view(request):
    ministries = Ministry.objects.filter(isActive=True)
    return render(request, 'events/reports.html', {
        'ministriesJson': MinistrySerializer(ministries, many=True).data,
    })


def server_attendance_view(request, server_id):
    server = get_object_or_404(Server, id=server_id)
    return render(request, 'events/server_attendance.html', {
        'serverJson': ServerSerializer(server).data,
    })


def audit_view(request):
    return render(request, 'events/audit.html')


def kiosko_view(request):
    return render(request, 'kiosko/index.html')
