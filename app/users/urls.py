from django.urls import path
from .views import *
from .logoutView import LogoutView
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

urlpatterns = [
    path('login/', login_view),
    path('dashboard/', dashboard_view),

    path('api/auth/login/', TokenObtainPairView.as_view()),
    path('api/auth/refresh/', TokenRefreshView.as_view()),
    path('api/auth/logout/', LogoutView.as_view()),
    path('api/auth/me/', me),
]