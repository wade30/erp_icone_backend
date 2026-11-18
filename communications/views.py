from django.db import transaction

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from users.models import User
from users.permissions import ERPModulePermission

from .models import CalendarEvent, Notification
from .serializers import CalendarEventSerializer, NotificationSerializer


class NotificationPagination(PageNumberPagination):
    page_size = 5


class CalendarEventViewSet(viewsets.ModelViewSet):
    queryset = CalendarEvent.objects.select_related("created_by").all()
    serializer_class = CalendarEventSerializer
    permission_classes = [IsAuthenticated, ERPModulePermission]
    permission_module = "calendar"

    @transaction.atomic
    def perform_create(self, serializer):
        event = serializer.save(created_by=self.request.user)
        self._notify_active_users(event)

    @transaction.atomic
    def perform_update(self, serializer):
        event = serializer.save()
        Notification.objects.filter(event=event).delete()
        self._notify_active_users(event)

    def _notify_active_users(self, event):
        recipients = User.objects.filter(is_active=True)
        message = (
            f"{event.get_event_type_display()} : {event.title}"
        )
        Notification.objects.bulk_create([
            Notification(
                recipient=recipient,
                event=event,
                message=message,
            )
            for recipient in recipients.iterator()
        ])


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = NotificationPagination

    def get_queryset(self):
        return (
            Notification.objects
            .filter(recipient=self.request.user)
            .select_related("event")
        )

    @action(detail=False, methods=["get"], url_path="unread-count")
    def unread_count(self, request):
        count = self.get_queryset().filter(is_read=False).count()
        return Response({"count": count})

    @action(detail=True, methods=["post"], url_path="mark-read")
    def mark_read(self, request, pk=None):
        notification = self.get_object()
        if not notification.is_read:
            notification.is_read = True
            notification.save(update_fields=("is_read",))
        return Response(self.get_serializer(notification).data)

    @action(detail=False, methods=["post"], url_path="mark-all-read")
    def mark_all_read(self, request):
        self.get_queryset().filter(is_read=False).update(is_read=True)
        return Response({"detail": "Toutes les notifications sont marquées comme lues."})
