from django.urls import path, include

from rest_framework.routers import SimpleRouter

from .views import (
    ServerViewSet,
    serversView
)

router = SimpleRouter()

router.register(r'api/servers',ServerViewSet,basename='servers')

urlpatterns = [
    path('servers/',serversView),
    path('',include(router.urls))
]