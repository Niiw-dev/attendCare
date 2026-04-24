from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response

def login_view(request):
    return render(request, 'login.html')

def dashboard_view(request):
    return render(request, 'dashboard.html')


class LogoutView(APIView):
    def post(self, request):
        return Response({"message": "Logout exitoso"})