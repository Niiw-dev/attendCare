from django.shortcuts import render

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import Server, ServerMinistry
from .serializers import ServerSerializer

from ministries.models import Ministry

from users.permissions import IsPastor


def serversView(request):

    serversData = list(
        Server.objects.values(
            'id',
            'firstName',
            'lastName',
            'document',
            'isActive'
        )
    )

    return render(request, 'servers/index.html',
        {
            'serversJson': serversData
        }
    )



class ServerViewSet(viewsets.ModelViewSet):

    queryset = Server.objects.all()

    serializer_class = ServerSerializer

    permission_classes = [IsAuthenticated, IsPastor]


    def get_queryset(self):

        queryset = Server.objects.prefetch_related('ministries')

        ministryId = self.request.query_params.get('ministryId')

        isActive = self.request.query_params.get('isActive')

        if ministryId:

            queryset = queryset.filter(ministries__id=ministryId)

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