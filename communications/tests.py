from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import CalendarEvent, Notification


User = get_user_model()


class CalendarEventApiTests(APITestCase):
    def setUp(self):
        self.secretary = User.objects.create_user(
            username="secretary",
            password="test-password",
            role="SECRETARY",
        )
        self.staff = User.objects.create_user(
            username="staff",
            password="test-password",
            role="STAFF",
        )
        self.inactive = User.objects.create_user(
            username="inactive",
            password="test-password",
            role="STAFF",
            is_active=False,
        )
        self.client.force_authenticate(self.secretary)

    def event_payload(self):
        return {
            "title": "Assemblée générale",
            "event_type": "CONVOCATION",
            "description": "Réunion du personnel",
            "location": "Salle principale",
            "starts_at": "2027-01-15T09:00:00Z",
            "ends_at": "2027-01-15T10:00:00Z",
        }

    def test_secretary_can_create_event_and_notify_active_users(self):
        response = self.client.post(
            reverse("calendar-event-list"),
            self.event_payload(),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        event = CalendarEvent.objects.get()
        self.assertEqual(event.created_by, self.secretary)
        self.assertSetEqual(
            set(Notification.objects.filter(event=event).values_list(
                "recipient_id",
                flat=True,
            )),
            {self.secretary.id, self.staff.id},
        )
        self.assertFalse(
            Notification.objects.filter(
                recipient=self.inactive,
                event=event,
            ).exists()
        )

    def test_staff_can_read_events_but_cannot_create_them(self):
        self.client.force_authenticate(self.staff)

        list_response = self.client.get(reverse("calendar-event-list"))
        event = CalendarEvent.objects.create(
            title="Réunion",
            event_type=CalendarEvent.Type.EVENT,
            starts_at="2027-01-15T09:00:00Z",
        )
        detail_response = self.client.get(
            reverse("calendar-event-detail", args=(event.id,))
        )
        create_response = self.client.post(
            reverse("calendar-event-list"),
            self.event_payload(),
            format="json",
        )

        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(detail_response.status_code, status.HTTP_200_OK)
        self.assertEqual(create_response.status_code, status.HTTP_403_FORBIDDEN)

    def test_event_end_must_be_after_start(self):
        payload = self.event_payload()
        payload["ends_at"] = "2027-01-15T08:00:00Z"

        response = self.client.post(
            reverse("calendar-event-list"),
            payload,
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(CalendarEvent.objects.exists())


class NotificationApiTests(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            username="owner",
            password="test-password",
            role="STAFF",
        )
        self.other_user = User.objects.create_user(
            username="other",
            password="test-password",
            role="STAFF",
        )
        self.event = CalendarEvent.objects.create(
            title="Réunion",
            event_type=CalendarEvent.Type.EVENT,
            starts_at="2027-02-01T10:00:00Z",
        )
        self.notification = Notification.objects.create(
            recipient=self.owner,
            event=self.event,
            message="Événement : Réunion",
        )
        self.other_notification = Notification.objects.create(
            recipient=self.other_user,
            event=self.event,
            message="Événement : Réunion",
        )
        self.client.force_authenticate(self.owner)

    def test_notification_list_only_returns_current_users_notifications(self):
        response = self.client.get(reverse("notification-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["id"], self.notification.id)

    def test_user_cannot_read_another_users_notification(self):
        response = self.client.post(
            reverse(
                "notification-mark-read",
                args=(self.other_notification.id,),
            )
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.other_notification.refresh_from_db()
        self.assertFalse(self.other_notification.is_read)

    def test_owner_can_read_notification_and_unread_count_updates(self):
        count_response = self.client.get(
            reverse("notification-unread-count")
        )
        read_response = self.client.post(
            reverse(
                "notification-mark-read",
                args=(self.notification.id,),
            )
        )
        updated_count_response = self.client.get(
            reverse("notification-unread-count")
        )

        self.assertEqual(count_response.data["count"], 1)
        self.assertEqual(read_response.status_code, status.HTTP_200_OK)
        self.assertTrue(read_response.data["is_read"])
        self.assertEqual(updated_count_response.data["count"], 0)
