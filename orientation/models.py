from django.db import models
from django.conf import settings


class Beneficiary(models.Model):

    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)

    phone = models.CharField(max_length=30)
    email = models.EmailField(blank=True)

    age = models.PositiveIntegerField(null=True, blank=True)
    education_level = models.CharField(max_length=120, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


class Appointment(models.Model):

    beneficiary = models.ForeignKey(
        Beneficiary,
        on_delete=models.PROTECT,
        related_name="appointments"
    )

    responsible = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT
    )

    appointment_date = models.DateTimeField()
    reason = models.TextField()

    completed = models.BooleanField(default=False)

    def __str__(self):
        return f"Rendez-vous {self.beneficiary}"


class OrientationRecord(models.Model):

    beneficiary = models.ForeignKey(
        Beneficiary,
        on_delete=models.PROTECT,
        related_name="orientations"
    )

    domain = models.CharField(max_length=150)
    recommendation = models.TextField()

    institution_referred = models.CharField(
        max_length=150,
        blank=True
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.domain