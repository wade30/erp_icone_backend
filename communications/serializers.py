from rest_framework import serializers

from .models import CalendarEvent, Notification


class CalendarEventSerializer(serializers.ModelSerializer):
    created_by_name = serializers.SerializerMethodField()

    class Meta:
        model = CalendarEvent
        fields = (
            "id",
            "title",
            "event_type",
            "description",
            "location",
            "starts_at",
            "ends_at",
            "created_by",
            "created_by_name",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "created_by",
            "created_by_name",
            "created_at",
            "updated_at",
        )

    def get_created_by_name(self, event):
        if not event.created_by:
            return ""
        return event.created_by.get_full_name() or event.created_by.username

    def validate(self, attrs):
        starts_at = attrs.get(
            "starts_at",
            getattr(self.instance, "starts_at", None),
        )
        ends_at = attrs.get(
            "ends_at",
            getattr(self.instance, "ends_at", None),
        )

        if starts_at and ends_at and ends_at <= starts_at:
            raise serializers.ValidationError({
                "ends_at": "La fin doit être postérieure au début."
            })

        return attrs


class NotificationSerializer(serializers.ModelSerializer):
    event_title = serializers.CharField(
        source="event.title",
        read_only=True,
    )
    event_type = serializers.CharField(
        source="event.event_type",
        read_only=True,
    )
    event_starts_at = serializers.DateTimeField(
        source="event.starts_at",
        read_only=True,
    )

    class Meta:
        model = Notification
        fields = (
            "id",
            "event",
            "event_title",
            "event_type",
            "event_starts_at",
            "message",
            "is_read",
            "created_at",
        )
        read_only_fields = fields
