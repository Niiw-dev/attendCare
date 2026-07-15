from django.urls import path, include

from rest_framework.routers import SimpleRouter

from .views import (
    ServerViewSet,
    serversView,
    serverDetailView,
)

router = SimpleRouter()

router.register(r'api/servers',ServerViewSet,basename='servers')

urlpatterns = [
    path('servers/',serversView),
    path('servers/<int:serverId>/detail/', serverDetailView, name='serverDetailView'),
    path('',include(router.urls))
]