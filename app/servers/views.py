from django.shortcuts import render

from rest_framework import viewsets
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



class ServerViewSet(viewsets.ModelViewSet):

    queryset = Server.objects.all()

    serializer_class = ServerSerializer

    permission_classes = [IsAuthenticated]


    def get_queryset(self):
        queryset = Server.objects.all()
        user = self.request.user
        ministryId = self.request.query_params.get('ministryId')
        isActive = self.request.query_params.get('isActive')

        # LIDER solo ve servidores de su ministerio
        if user.role == 'LIDER':
            from ministries.models import Ministry
            my_ministry = Ministry.objects.filter(leaderAssigned=user).first()
            if my_ministry:
                queryset = queryset.filter(ministries=my_ministry)
            else:
                return Server.objects.none()

        if ministryId:
            queryset = queryset.filter(ministries=ministryId)

        if isActive is not None:
            queryset = queryset.filter(isActive=isActive == 'true')

        return queryset


    @action(detail=True, methods=['post'])
    def ministries(self, request, pk=None):

        server = self.get_object()

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

        server.isActive = False

        server.save()

        return Response({
            'message': 'Servidor desactivado'
        })


    @action(detail=True, methods=['patch'])
    def activate(self, request, pk=None):

        server = self.get_object()

        server.isActive = True

        server.save()

        return Response({
            'message': 'Servidor activado'
        })