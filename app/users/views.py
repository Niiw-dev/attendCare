from django.shortcuts import render
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes
from users.permissions import IsPastor
from rest_framework.response import Response


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

