from django.db import models


class Client(models.Model):

    name = models.CharField(max_length=150)
    contact_person = models.CharField(max_length=120, blank=True)

    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=30, blank=True)

    address = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Contract(models.Model):

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Brouillon"
        ACTIVE = "ACTIVE", "Actif"
        COMPLETED = "COMPLETED", "Terminé"
        CANCELLED = "CANCELLED", "Annulé"

    reference = models.CharField(max_length=50, unique=True)

    client = models.ForeignKey(
        Client,
        on_delete=models.PROTECT,
        related_name="contracts"
    )

    title = models.CharField(max_length=150)
    description = models.TextField(blank=True)

    amount = models.DecimalField(
        max_digits=18,
        decimal_places=2
    )

    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT
    )

    def __str__(self):
        return self.reference


class ServiceOrder(models.Model):

    contract = models.ForeignKey(
        Contract,
        on_delete=models.PROTECT,
        related_name="orders"
    )

    title = models.CharField(max_length=150)
    description = models.TextField(blank=True)

    amount = models.DecimalField(
        max_digits=18,
        decimal_places=2
    )

    delivery_date = models.DateField(null=True, blank=True)
    completed = models.BooleanField(default=False)

    def __str__(self):
        return self.title