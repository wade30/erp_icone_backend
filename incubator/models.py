from django.db import models
from django.conf import settings


class Entrepreneur(models.Model):

    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)

    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=30)

    sector = models.CharField(max_length=120)
    company_name = models.CharField(max_length=150, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


class Project(models.Model):

    class Status(models.TextChoices):
        IDEA = "IDEA", "Idée"
        PREINCUBATION = "PREINCUBATION", "Préincubation"
        INCUBATION = "INCUBATION", "Incubation"
        ACCELERATION = "ACCELERATION", "Accélération"
        COMPLETED = "COMPLETED", "Terminé"

    name = models.CharField(max_length=150)

    entrepreneur = models.ForeignKey(
        Entrepreneur,
        on_delete=models.PROTECT,
        related_name="projects"
    )

    description = models.TextField()
    sector = models.CharField(max_length=120)

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.IDEA
    )

    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)

    estimated_budget = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=0
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class CoachingSession(models.Model):

    project = models.ForeignKey(
        Project,
        on_delete=models.PROTECT,
        related_name="coaching_sessions"
    )

    coach = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT
    )

    session_date = models.DateTimeField()
    subject = models.CharField(max_length=150)
    notes = models.TextField(blank=True)

    def __str__(self):
        return self.subject