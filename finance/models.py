
from django.db import models
from django.conf import settings
import uuid
from django.utils import timezone


# ============================================================
# 1. GÉNÉRATION DES RÉFÉRENCES
# ============================================================

def generate_reference(prefix, operation_date=None):
    year = (
        operation_date.year
        if operation_date
        else timezone.localdate().year
    )

    unique_code = uuid.uuid4().hex[:12].upper()

    return f"{prefix}-{year}-{unique_code}"


# ============================================================
# 2. COMPTES BANCAIRES
# ============================================================

class BankAccount(models.Model):

    name = models.CharField(max_length=150)
    bank_name = models.CharField(max_length=150, blank=True)

    account_number = models.CharField(
        max_length=100,
        blank=True
    )

    balance = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=0
    )

    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


# ============================================================
# 3. ENCAISSEMENTS
# ============================================================

class Receipt(models.Model):

    class PaymentMethod(models.TextChoices):
        CASH = "CASH", "Espèces"
        BANK = "BANK", "Virement bancaire"
        WAVE = "WAVE", "Wave"
        ORANGE_MONEY = "ORANGE_MONEY", "Orange Money"
        OTHER = "OTHER", "Autre"

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Brouillon"
        COMPLETED = "COMPLETED", "Enregistré"

    reference = models.CharField(
        max_length=50,
        unique=True,
        editable=False,
        blank=True,
    )

    payment_reference = models.CharField(
        max_length=100,
        unique=True,
        null=True,
        blank=True,
        editable=False,
    )

    date = models.DateField(
        null=True,
        blank=True
    )

    description = models.TextField(blank=True)

    service = models.CharField(
        max_length=20,
        blank=True
    )

    project = models.CharField(
        max_length=150,
        blank=True
    )

    client = models.CharField(
        max_length=150,
        blank=True
    )

    amount = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        null=True,
        blank=True
    )

    payment_method = models.CharField(
        max_length=20,
        choices=PaymentMethod.choices,
        blank=True
    )

    bank_account = models.ForeignKey(
        BankAccount,
        on_delete=models.PROTECT,
        null=True,
        blank=True
    )

    budget_line = models.ForeignKey(
        "budgeting.BudgetLine",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="receipts",
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT
    )

    validated = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.reference

    def save(self, *args, **kwargs):

        if not self.reference:
            self.reference = generate_reference("REC", self.date)

        if not self.payment_reference:
            self.payment_reference = generate_reference("PAY", self.date)

        super().save(*args, **kwargs)


# ============================================================
# 4. DÉCAISSEMENTS
# ============================================================

class CashExpense(models.Model):

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Brouillon"
        COMPLETED = "COMPLETED", "Enregistré"

    reference = models.CharField(
        max_length=50,
        unique=True,
        editable=False,
        blank=True,
    )

    payment_reference = models.CharField(
        max_length=100,
        unique=True,
        null=True,
        blank=True,
        editable=False,
    )

    date = models.DateField(
        null=True,
        blank=True
    )

    service = models.CharField(
        max_length=20,
        blank=True
    )

    category = models.CharField(
        max_length=100,
        blank=True
    )

    description = models.TextField(blank=True)

    supplier = models.CharField(
        max_length=150,
        blank=True
    )

    amount = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        null=True,
        blank=True
    )

    payment_method = models.CharField(
        max_length=20,
        choices=Receipt.PaymentMethod.choices,
        blank=True
    )

    bank_account = models.ForeignKey(
        BankAccount,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="cash_expenses",
    )

    external_payment_reference = models.CharField(
        max_length=150,
        blank=True,
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT
    )

    # Lien avec une demande de dépense.
    # Facultatif pour les décaissements directs.

    expense_request = models.OneToOneField(
        "ExpenseRequest",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="cash_expense",
    )

    budget_line = models.ForeignKey(
        "budgeting.BudgetLine",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="cash_expenses",
    )
    
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="cash_expenses",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.reference

    def save(self, *args, **kwargs):

        if not self.reference:
            self.reference = generate_reference("DEP", self.date)

        if not self.payment_reference:
            self.payment_reference = generate_reference("PAY", self.date)

        super().save(*args, **kwargs)


# ============================================================
# 5. DEMANDES DE DÉPENSES
# ============================================================

class ExpenseRequest(models.Model):

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Brouillon"
        SUBMITTED = "SUBMITTED", "Soumise"
        APPROVED = "APPROVED", "Approuvée"
        REJECTED = "REJECTED", "Rejetée"
        PAID = "PAID", "Payée"

    reference = models.CharField(
        max_length=50,
        unique=True,
        editable=False,
        blank=True,
    )

    date = models.DateField(null=True, blank=True)

    service = models.CharField(
        max_length=20,
        blank=True
    )

    category = models.CharField(
        max_length=100,
        blank=True
    )

    budget_line = models.ForeignKey(
        "budgeting.BudgetLine",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="expense_requests",
    )

    description = models.TextField(blank=True)

    amount = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        null=True,
        blank=True
    )

    supplier = models.CharField(
        max_length=150,
        blank=True
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT
    )

    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="expense_requests"
    )

    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="approved_expenses"
    )

    approved_at = models.DateTimeField(
        null=True,
        blank=True
    )

    rejected_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="rejected_expense_requests"
    )

    rejected_at = models.DateTimeField(
        null=True,
        blank=True
    )

    rejection_reason = models.TextField(blank=True)

    paid_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="paid_expense_requests"
    )

    paid_at = models.DateField(
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.reference

    def save(self, *args, **kwargs):

        if not self.reference:
            self.reference = generate_reference("DEM", self.date)

        super().save(*args, **kwargs)
