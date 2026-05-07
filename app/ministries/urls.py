from django.urls import path, include

from rest_framework.routers import SimpleRouter

from .views import *

router = SimpleRouter()

router.register(
    r'api/ministries',
    MinistryViewSet
)

urlpatterns = [
    path('ministries/',ministriesView, name='ministries'),
    path('',include(router.urls)),
]