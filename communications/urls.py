from rest_framework.routers import DefaultRouter

from .views import CalendarEventViewSet, NotificationViewSet

router = DefaultRouter()
router.register("events", CalendarEventViewSet, basename="calendar-event")
router.register("notifications", NotificationViewSet, basename="notification")

urlpatterns = router.urls
