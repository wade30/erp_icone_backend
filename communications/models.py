from django.conf import settings
from django.db import models
from django.db.models import UniqueConstraint


class CalendarEvent(models.Model):
    class Type(models.TextChoices):
        CONVOCATION = "CONVOCATION", "Convocation"
        EVENT = "EVENT", "Événement"

    title = models.CharField(max_length=180)
    event_type = models.CharField(
        max_length=20,
        choices=Type.choices,
        default=Type.EVENT,
    )
    description = models.TextField(blank=True)
    location = models.CharField(max_length=255, blank=True)
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField(blank=True, null=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="calendar_events",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("starts_at", "id")

    def __str__(self):
        return self.title


class Notification(models.Model):
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    event = models.ForeignKey(
        CalendarEvent,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    message = models.CharField(max_length=255)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at", "-id")
        constraints = [
            UniqueConstraint(
                fields=("recipient", "event"),
                name="unique_notification_per_event_recipient",
            ),
        ]

    def __str__(self):
        return f"{self.recipient} — {self.message}"
