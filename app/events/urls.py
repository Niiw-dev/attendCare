from django.urls import path, include
from rest_framework.routers import SimpleRouter

from .views import *


router = SimpleRouter()

router.register(r'api/events', EventViewSet)

router.register(r'api/types',EventTypeViewSet)

router.register(r'api/status', EventStatusViewSet)

router.register('recurring-events', RecurringEventViewSet)

urlpatterns = [
    path('events/view/', eventsView, name='eventListView'),
    path('events/create/', createEventView, name='eventCreateView'),
    path('events/<int:eventId>/detail/', detailEventView, name='eventDetailView'),
    path('events/types/view/', eventTypesView, name='eventTypesView'),
    path('events/statuses/view/', eventStatusesView, name='eventStatusesView'),
    path('events/recurring/view/',recurringEventsView, name='recurringEventsView'),
    path('',include(router.urls)),
]