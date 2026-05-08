from django.shortcuts import render

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import Ministry
from .serializers import MinistrySerializer

from users.permissions import IsPastor


def ministriesView(request):

    ministriesData = list(
        Ministry.objects.all().values(
            'id',
            'name',
            'description',
            'leaderAssigned_id',
            'isActive'
        )
    )

    return render(request, 'ministries/index.html', {
        'ministriesJson': ministriesData
    })



class MinistryViewSet(viewsets.ModelViewSet):

    queryset = Ministry.objects.all()

    serializer_class = MinistrySerializer

    permission_classes = [IsAuthenticated,IsPastor]


    def get_queryset(self):

        isActive = self.request.query_params.get('isActive')

        query = Ministry.objects.all()

        if isActive is not None:
            query = query.filter(isActive=isActive == 'true')

        return query


    @action(detail=True, methods=['patch'])
    def deactivate(self, request, pk=None):

        ministry = self.get_object()

        ministry.isActive = False

        ministry.save()

        return Response({
            "message": "Ministerio desactivado"
        })


    @action(detail=True, methods=['patch'])
    def activate(self, request, pk=None):

        ministry = self.get_object()

        ministry.isActive = True

        ministry.save()

        return Response({
            "message": "Ministerio activado"
        })