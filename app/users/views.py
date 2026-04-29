import json

from django.shortcuts import render
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import User
from .serializers import UserSerializer
from .permissions import IsPastor


def usuarios_view(request):
    role = request.GET.get('role')
    is_active = request.GET.get('is_active')

    qs = User.objects.all()

    if role:
        qs = qs.filter(role=role)
    if is_active is not None:
        qs = qs.filter(is_active=is_active == 'true')

    usuarios_data = list(qs.values('id', 'username', 'email', 'role', 'is_active'))

    return render(request, 'pastor/usuarios.html', {
        'usuarios_json': usuarios_data
    })


def login_view(request):
    return render(request, 'login.html')


def dashboard_view(request):
    return render(request, 'dashboard.html')


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def me(request):
    user = request.user

    return Response({
        "id": user.id,
        "username": user.username,
        "role": user.role
    })


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated, IsPastor]

    def get_queryset(self):
        role = self.request.query_params.get('role')
        is_active = self.request.query_params.get('is_active')

        qs = User.objects.all()

        if role:
            qs = qs.filter(role=role)

        if is_active is not None:
            qs = qs.filter(is_active=is_active == 'true')

        return qs

    @action(detail=True, methods=['patch'])
    def desactivar(self, request, pk=None):
        user = self.get_object()

        if request.user.id == user.id:
            return Response({"error": "No puedes desactivarte a ti mismo"}, status=400)
        
        user.is_active = False
        user.save()

        return Response({"message": "Usuario desactivado"})
    
    @action(detail=True, methods=['patch'])
    def activar(self, request, pk=None):
        user = self.get_object()

        if request.user.id == user.id:
            return Response({"error": "No puedes activarte a ti mismo"}, status=400)

        user.is_active = True
        user.save()

        return Response({"message": "Usuario activado"})
