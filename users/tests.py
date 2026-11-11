from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase


User = get_user_model()


class RegistrationTests(APITestCase):
    def test_registration_creates_inactive_staff_account(self):
        response = self.client.post(
            reverse("user-register"),
            {
                "username": "newmember",
                "email": "newmember@example.com",
                "first_name": "New",
                "last_name": "Member",
                "telephone": "+221 77 000 00 00",
                "fonction": "Développeur",
                "service": User.Service.INSTITUTE,
                "password": "J9!r4#vQ2sX8",
                "role": "DIRECTOR",
                "is_staff": True,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(username="newmember")
        self.assertFalse(user.is_active)
        self.assertFalse(user.is_staff)
        self.assertEqual(user.role, User.Role.STAFF)
        self.assertEqual(user.service, User.Service.INSTITUTE)
        self.assertEqual(user.telephone, "+221 77 000 00 00")
        self.assertEqual(user.fonction, "Développeur")

    def test_registration_rejects_weak_passwords(self):
        response = self.client.post(
            reverse("user-register"),
            {
                "username": "newmember",
                "email": "newmember@example.com",
                "first_name": "New",
                "last_name": "Member",
                "password": "password",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(User.objects.filter(username="newmember").exists())

    def test_pending_user_cannot_log_in(self):
        User.objects.create_user(
            username="pending",
            password="J9!r4#vQ2sX8",
            is_active=False,
        )

        response = self.client.post(
            reverse("auth-login"),
            {"username": "pending", "password": "J9!r4#vQ2sX8"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_active_user_can_log_in_and_read_own_profile(self):
        User.objects.create_user(
            username="active",
            password="J9!r4#vQ2sX8",
            is_active=True,
        )

        login_response = self.client.post(
            reverse("auth-login"),
            {"username": "active", "password": "J9!r4#vQ2sX8"},
            format="json",
        )

        self.assertEqual(login_response.status_code, status.HTTP_200_OK)
        profile_response = self.client.get(reverse("auth-current-user"))

        self.assertEqual(profile_response.status_code, status.HTTP_200_OK)
        self.assertEqual(profile_response.data["username"], "active")
        self.assertFalse(profile_response.data["is_staff"])
