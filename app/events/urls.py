from django.urls import path, include
from rest_framework.routers import SimpleRouter

from .views import *

router = SimpleRouter()
router.register(r'api/events', EventViewSet)
router.register(r'api/types', EventTypeViewSet)
router.register(r'api/status', EventStatusViewSet)
router.register(r'api/recurringEvents', RecurringEventViewSet)
router.register(r'api/assignments', AssignmentViewSet)
router.register(r'api/attendances', AttendanceViewSet)
router.register(r'api/reconciliations', ReconciliationViewSet)
router.register(r'api/audit', AuditLogViewSet)

urlpatterns = [
    # HTML views
    path('events/view/', eventsView, name='eventListView'),
    path('events/<int:eventId>/detail/', detailEventView, name='eventDetailView'),
    path('events/types/view/', eventTypesView, name='eventTypesView'),
    path('events/statuses/view/', eventStatusesView, name='eventStatusesView'),
    path('events/recurring/view/', recurringEventsView, name='recurringEventsView'),
    path('events/reports/server/<int:server_id>/attendance/', server_attendance_view, name='serverAttendanceView'),
    path('events/reports/', events_reports_view, name='eventsReports'),
    path('audit/', audit_view, name='auditView'),
    path('kiosko/', kiosko_view, name='kioskoView'),

    # Kiosko API
    path('api/kiosko/auth/', kiosko_auth, name='kioskoAuth'),
    path('api/kiosko/active-events/', kiosko_active_events, name='kioskoActiveEvents'),
    path('api/kiosko/register/', kiosko_register, name='kioskoRegister'),
    path('api/kiosko/checkout/', kiosko_checkout, name='kioskoCheckout'),

    # Reportes API
    path('api/reports/server/<int:server_id>/attendance/', report_server_attendance, name='reportServerAttendance'),
    path('api/reports/ministry/<int:ministry_id>/indicators/', report_ministry_indicators, name='reportMinistryIndicators'),
    path('api/reports/general/', report_general, name='reportGeneral'),

    path('', include(router.urls)),
]
