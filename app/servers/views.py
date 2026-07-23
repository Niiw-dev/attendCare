from django.shortcuts import render

from rest_framework import viewsets, status as http_status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import Server, ServerMinistry
from .serializers import ServerSerializer

from ministries.models import Ministry

from users.permissions import IsPastor
from rest_framework.permissions import IsAuthenticated


def serversView(request):
    from ministries.serializers import MinistrySerializer
    from ministries.models import Ministry

    servers = Server.objects.prefetch_related('ministries')
    serversData = ServerSerializer(servers, many=True).data
    return render(request, 'servers/index.html', {
        'serversJson': serversData,
        'ministriesJson': MinistrySerializer(Ministry.objects.filter(isActive=True), many=True).data,
    })


def serverDetailView(request, serverId):

    server = Server.objects.prefetch_related('ministries').get(id=serverId)

    serverMinistries = ServerMinistry.objects.filter(server=server).select_related('ministry')

    return render(request, 'servers/detail.html', {
        'serverJson': ServerSerializer(server).data,
        'serverMinistriesJson': [
            {
                'id': sm.ministry.id,
                'name': sm.ministry.name,
                'joinedAt': sm.joinedAt.isoformat(),
                'isActive': sm.ministry.isActive,
            }
            for sm in serverMinistries
        ],
    })


def _get_user_ministry(user):
    if user.role == 'LIDER':
        return Ministry.objects.filter(leaderAssigned=user).first()
    return None


def _is_own_ministry_server(server, user):
    my_ministry = _get_user_ministry(user)
    if not my_ministry:
        return user.role == 'PASTOR'
    return server.ministries.filter(id=my_ministry.id).exists()


class ServerViewSet(viewsets.ModelViewSet):

    queryset = Server.objects.all()

    serializer_class = ServerSerializer

    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        ministryId = self.request.query_params.get('ministryId')
        isActive = self.request.query_params.get('isActive')

        if user.role == 'LIDER':
            my_ministry = Ministry.objects.filter(leaderAssigned=user).first()
            if my_ministry:
                own_servers = list(Server.objects.filter(ministries=my_ministry))
                other_servers = list(Server.objects.exclude(ministries=my_ministry))
                queryset = own_servers + other_servers
            else:
                queryset = list(Server.objects.none())
        else:
            queryset = list(Server.objects.all())

        if ministryId:
            queryset = [s for s in queryset if s.ministries.filter(id=ministryId).exists()]

        if isActive is not None:
            is_active = isActive == 'true'
            queryset = [s for s in queryset if s.isActive == is_active]

        return queryset

    def perform_create(self, serializer):
        server = serializer.save()
        user = self.request.user
        if user.role == 'LIDER':
            my_ministry = Ministry.objects.filter(leaderAssigned=user).first()
            if my_ministry:
                ServerMinistry.objects.create(server=server, ministry=my_ministry)

    def perform_update(self, serializer):
        server = self.get_object()
        user = self.request.user
        if user.role == 'LIDER' and not _is_own_ministry_server(server, user):
            return Response({'error': 'No tienes permisos para modificar este servidor'}, status=http_status.HTTP_403_FORBIDDEN)
        serializer.save()

    def update(self, request, *args, **kwargs):
        server = self.get_object()
        user = request.user
        if user.role == 'LIDER' and not _is_own_ministry_server(server, user):
            return Response({'error': 'No tienes permisos para modificar este servidor'}, status=http_status.HTTP_403_FORBIDDEN)
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        server = self.get_object()
        user = request.user
        if user.role == 'LIDER' and not _is_own_ministry_server(server, user):
            return Response({'error': 'No tienes permisos para modificar este servidor'}, status=http_status.HTTP_403_FORBIDDEN)
        return super().partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        server = self.get_object()
        user = request.user
        if user.role == 'LIDER' and not _is_own_ministry_server(server, user):
            return Response({'error': 'No tienes permisos para eliminar este servidor'}, status=http_status.HTTP_403_FORBIDDEN)
        return super().destroy(request, *args, **kwargs)

    @action(detail=True, methods=['post'])
    def ministries(self, request, pk=None):

        server = self.get_object()
        user = request.user

        if user.role == 'LIDER' and not _is_own_ministry_server(server, user):
            return Response({'error': 'No tienes permisos para modificar este servidor'}, status=http_status.HTTP_403_FORBIDDEN)

        ministryIds = request.data.get('ministryIds', [])

        ServerMinistry.objects.filter(server=server).delete()

        ministries = Ministry.objects.filter(id__in=ministryIds, isActive=True)

        for ministry in ministries:

            ServerMinistry.objects.create(server=server, ministry=ministry)

        return Response({
            'message': 'Ministerios actualizados'
        })


    @action(detail=True, methods=['patch'])
    def deactivate(self, request, pk=None):

        server = self.get_object()
        user = request.user

        if user.role == 'LIDER' and not _is_own_ministry_server(server, user):
            return Response({'error': 'No tienes permisos para desactivar este servidor'}, status=http_status.HTTP_403_FORBIDDEN)

        server.isActive = False

        server.save()

        return Response({
            'message': 'Servidor desactivado'
        })


    @action(detail=True, methods=['patch'])
    def activate(self, request, pk=None):

        server = self.get_object()
        user = request.user

        if user.role == 'LIDER' and not _is_own_ministry_server(server, user):
            return Response({'error': 'No tienes permisos para activar este servidor'}, status=http_status.HTTP_403_FORBIDDEN)

        server.isActive = True

        server.save()

        return Response({
            'message': 'Servidor activado'
        })