from django.urls import path, include
from .views import *
from .logoutView import LogoutView
from rest_framework_simplejwt.views import (TokenObtainPairView, TokenRefreshView,)

from rest_framework.routers import SimpleRouter

router = SimpleRouter()
router.register(r'api/usuarios', UserViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('login/', loginView),
    path('usuarios/', usuariosView),
    path('dashboard/', dashboardView),

    path('api/auth/login/', TokenObtainPairView.as_view()),
    path('api/auth/refresh/', TokenRefreshView.as_view()),
    path('api/auth/logout/', LogoutView.as_view()),
    path('api/auth/me/', me),
]

