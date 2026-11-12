from django.db import models


class Course(models.Model):

    title = models.CharField(max_length=150)
    description = models.TextField(blank=True)

    duration_hours = models.PositiveIntegerField(default=0)

    price = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=0
    )

    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.title


class Learner(models.Model):

    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)

    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=30)

    address = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


class Enrollment(models.Model):

    class Status(models.TextChoices):
        PENDING = "PENDING", "En attente"
        CONFIRMED = "CONFIRMED", "Confirmée"
        COMPLETED = "COMPLETED", "Terminée"
        CANCELLED = "CANCELLED", "Annulée"

    learner = models.ForeignKey(
        Learner,
        on_delete=models.PROTECT,
        related_name="enrollments"
    )

    course = models.ForeignKey(
        Course,
        on_delete=models.PROTECT
    )

    enrollment_date = models.DateField()

    amount_due = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=0
    )

    amount_paid = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=0
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )

    def __str__(self):
        return f"{self.learner} - {self.course}"