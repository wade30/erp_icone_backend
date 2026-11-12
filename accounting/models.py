
import uuid
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone


# ============================================================
# 1. GÉNÉRATION DES RÉFÉRENCES COMPTABLES
# ============================================================

def generate_accounting_reference(operation_date=None):
    year = (
        operation_date.year
        if operation_date
        else timezone.localdate().year
    )

    unique_code = uuid.uuid4().hex[:12].upper()

    return f"ECR-{year}-{unique_code}"


# ============================================================
# 2. PLAN COMPTABLE
# ============================================================

class Account(models.Model):

    class AccountType(models.TextChoices):
        ASSET = "ASSET", "Actif"
        LIABILITY = "LIABILITY", "Passif"
        EQUITY = "EQUITY", "Capitaux propres"
        INCOME = "INCOME", "Produits"
        EXPENSE = "EXPENSE", "Charges"

    code = models.CharField(
        max_length=20,
        unique=True,
    )

    name = models.CharField(
        max_length=150,
    )

    account_type = models.CharField(
        max_length=20,
        choices=AccountType.choices,
    )

    is_active = models.BooleanField(
        default=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["code"]
        verbose_name = "Compte comptable"
        verbose_name_plural = "Comptes comptables"

    def __str__(self):
        return f"{self.code} - {self.name}"


# ============================================================
# 3. JOURNAUX COMPTABLES
# ============================================================

class Journal(models.Model):

    code = models.CharField(
        max_length=20,
        unique=True,
    )

    name = models.CharField(
        max_length=150,
    )

    is_active = models.BooleanField(
        default=True,
    )

    class Meta:
        ordering = ["code"]
        verbose_name = "Journal comptable"
        verbose_name_plural = "Journaux comptables"

    def __str__(self):
        return f"{self.code} - {self.name}"


# ============================================================
# 4. ÉCRITURES COMPTABLES
# ============================================================

class AccountingEntry(models.Model):

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Brouillon"
        POSTED = "POSTED", "Comptabilisée"
        CANCELLED = "CANCELLED", "Annulée"

    reference = models.CharField(
        max_length=50,
        unique=True,
        editable=False,
        blank=True,
    )

    date = models.DateField(
        default=timezone.localdate,
    )

    journal = models.ForeignKey(
        Journal,
        on_delete=models.PROTECT,
        related_name="entries",
    )

    description = models.TextField()

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
    )

    receipt = models.OneToOneField(
        "finance.Receipt",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="accounting_entry",
    )

    cash_expense = models.OneToOneField(
        "finance.CashExpense",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="accounting_entry",
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="accounting_entries",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["-date", "-created_at"]
        verbose_name = "Écriture comptable"
        verbose_name_plural = "Écritures comptables"

        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(receipt__isnull=True)
                    | Q(cash_expense__isnull=True)
                ),
                name="accounting_entry_one_operation_only",
            ),
        ]

    def __str__(self):
        return self.reference

    @property
    def is_automatic(self):
        return bool(self.receipt_id or self.cash_expense_id)

    def validate_balance(self):

        lines = self.lines.all()

        if lines.count() < 2:
            raise ValidationError(
                "Une écriture doit contenir au moins deux lignes."
            )

        totals = lines.aggregate(
            total_debit=models.Sum("debit"),
            total_credit=models.Sum("credit"),
        )

        debit = totals["total_debit"] or Decimal("0.00")
        credit = totals["total_credit"] or Decimal("0.00")

        if debit <= 0 or credit <= 0:
            raise ValidationError(
                "Une écriture doit comporter un débit "
                "et un crédit positifs."
            )

        if debit != credit:
            raise ValidationError(
                f"Écriture déséquilibrée : "
                f"débit = {debit}, crédit = {credit}."
            )

    def clean(self):

        super().clean()

        if self.receipt_id and self.cash_expense_id:
            raise ValidationError(
                "Une écriture ne peut pas être liée simultanément "
                "à un encaissement et à un décaissement."
            )

        if self.status == self.Status.POSTED and self.pk:
            self.validate_balance()

    def save(self, *args, **kwargs):

        if not self.reference:
            self.reference = generate_accounting_reference(
                self.date
            )

        if self.pk:
            old_entry = (
                AccountingEntry.objects
                .filter(pk=self.pk)
                .first()
            )

            if old_entry and old_entry.status in [
                self.Status.POSTED,
                self.Status.CANCELLED,
            ]:
                raise ValidationError(
                    "Une écriture comptabilisée ou annulée "
                    "ne peut plus être modifiée."
                )

        if self.status == self.Status.POSTED:
            self.validate_balance()

        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):

        if self.status in [
            self.Status.POSTED,
            self.Status.CANCELLED,
        ]:
            raise ValidationError(
                "Une écriture comptabilisée ou annulée "
                "ne peut pas être supprimée."
            )

        super().delete(*args, **kwargs)


# ============================================================
# 5. LIGNES DES ÉCRITURES COMPTABLES
# ============================================================

class EntryLine(models.Model):

    class AccountingService(models.TextChoices):
        GENERAL = "GENERAL", "Direction générale"
        INSTITUTE = "INSTITUTE", "Institut numérique"
        INCUBATOR = "INCUBATOR", "Incubateur"
        MARKETING = "MARKETING", "Agence marketing"
        ORIENTATION = "ORIENTATION", "Accueil et orientation"
        PRESCHOOL = "PRESCHOOL", "Préscolaire"

    entry = models.ForeignKey(
        AccountingEntry,
        on_delete=models.PROTECT,
        related_name="lines",
    )

    account = models.ForeignKey(
        Account,
        on_delete=models.PROTECT,
        related_name="entry_lines",
    )

    service = models.CharField(
        max_length=20,
        choices=AccountingService.choices,
        default=AccountingService.GENERAL,
    )

    description = models.CharField(
        max_length=255,
        blank=True,
    )

    debit = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    credit = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    class Meta:
        ordering = ["id"]
        verbose_name = "Ligne comptable"
        verbose_name_plural = "Lignes comptables"

    def __str__(self):
        return (
            f"{self.account.code} - "
            f"Débit : {self.debit} / Crédit : {self.credit}"
        )

    def clean(self):

        super().clean()

        if self.debit < 0 or self.credit < 0:
            raise ValidationError(
                "Les montants ne peuvent pas être négatifs."
            )

        if self.debit > 0 and self.credit > 0:
            raise ValidationError(
                "Une ligne ne peut pas comporter simultanément "
                "un débit et un crédit."
            )

        if self.debit == 0 and self.credit == 0:
            raise ValidationError(
                "Une ligne doit comporter un débit "
                "ou un crédit."
            )

        if self.account_id and not self.account.is_active:
            raise ValidationError(
                "Le compte comptable sélectionné est inactif."
            )

        if self.entry_id and self.entry.status in [
            AccountingEntry.Status.POSTED,
            AccountingEntry.Status.CANCELLED,
        ]:
            raise ValidationError(
                "Impossible de modifier une ligne appartenant "
                "à une écriture verrouillée."
            )

    def save(self, *args, **kwargs):

        self.full_clean()

        if self.entry_id:
            entry = AccountingEntry.objects.get(
                pk=self.entry_id
            )

            if entry.status in [
                AccountingEntry.Status.POSTED,
                AccountingEntry.Status.CANCELLED,
            ]:
                raise ValidationError(
                    "Impossible de modifier une ligne "
                    "d'une écriture verrouillée."
                )

        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):

        if self.entry.status in [
            AccountingEntry.Status.POSTED,
            AccountingEntry.Status.CANCELLED,
        ]:
            raise ValidationError(
                "Impossible de supprimer une ligne "
                "d'une écriture verrouillée."
            )

        super().delete(*args, **kwargs)
