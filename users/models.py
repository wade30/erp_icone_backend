from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):

    class Role(models.TextChoices):
        SECRETARY = "SECRETARY", "Secrétaire de direction"
        DIRECTOR = "DIRECTOR", "Direction générale"
        PDG = "PDG", "PDG"
        FINANCE = "FINANCE", "Responsable financier"
        ACCOUNTANT = "ACCOUNTANT", "Comptable"
        SERVICE_MANAGER = "SERVICE_MANAGER", "Responsable de service"
        STAFF = "STAFF", "Collaborateur"

    class Service(models.TextChoices):
        GENERAL = "GENERAL", "Direction générale"
        INSTITUTE = "INSTITUTE", "Institut numérique"
        INCUBATOR = "INCUBATOR", "Incubateur"
        MARKETING = "MARKETING", "Agence marketing"
        ORIENTATION = "ORIENTATION", "Accueil et orientation"
        PRESCHOOL = "PRESCHOOL", "Préscolaire"

    role = models.CharField(
        max_length=30,
        choices=Role.choices,
        default=Role.STAFF
    )

    service = models.CharField(
        max_length=20,
        choices=Service.choices,
        default=Service.GENERAL
    )

    telephone = models.CharField(max_length=30, blank=True)
    fonction = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return f"{self.get_full_name() or self.username}"