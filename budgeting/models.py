from decimal import Decimal
from django.utils import timezone
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from django.db.models import Sum
from django.db.models.functions import Coalesce


# ============================================================
# 1. BUDGET
# ============================================================

class Budget(models.Model):

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Brouillon"
        SUBMITTED = "SUBMITTED", "Soumis"
        APPROVED = "APPROVED", "Approuvé"
        CLOSED = "CLOSED", "Clôturé"

    class Service(models.TextChoices):
        GENERAL = "GENERAL", "Direction générale"
        INSTITUTE = "INSTITUTE", "Institut des métiers du numérique"
        INCUBATOR = "INCUBATOR", "Incubateur"
        MARKETING = "MARKETING", "Agence marketing"
        ORIENTATION = "ORIENTATION", "Accueil et orientation"
        PRESCHOOL = "PRESCHOOL", "Préscolaire"

    name = models.CharField(max_length=150)

    service = models.CharField(
        max_length=20,
        choices=Service.choices,
    )

    fiscal_year = models.PositiveIntegerField()

    start_date = models.DateField()
    end_date = models.DateField()

    funding_source = models.CharField(
        max_length=150,
        blank=True,
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="budgets_created",
    )

    created_at = models.DateTimeField(default=timezone.now)

    updated_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-fiscal_year", "service", "name"]

    def clean(self):
        errors = {}

        if self.start_date and self.end_date:
            if self.end_date < self.start_date:
                errors["end_date"] = (
                    "La date de fin doit être postérieure "
                    "ou égale à la date de début."
                )

        if self.start_date and self.fiscal_year:
            if self.start_date.year != self.fiscal_year:
                errors["start_date"] = (
                    "La date de début doit correspondre "
                    "à l'exercice budgétaire."
                )

        if errors:
            raise ValidationError(errors)

    @property
    def total_income_forecast(self):
        return self.lines.filter(
            nature=BudgetLine.Nature.INCOME
        ).aggregate(
            total=Coalesce(
                Sum("revised_amount"),
                Decimal("0.00"),
            )
        )["total"]

    @property
    def total_expense_forecast(self):
        return self.lines.filter(
            nature=BudgetLine.Nature.EXPENSE
        ).aggregate(
            total=Coalesce(
                Sum("revised_amount"),
                Decimal("0.00"),
            )
        )["total"]

    @property
    def total_income_realized(self):
        return sum(
            (line.realized_amount for line in self.lines.filter(
                nature=BudgetLine.Nature.INCOME
            )),
            Decimal("0.00"),
        )

    @property
    def total_expense_paid(self):
        return sum(
            (line.calculated_paid_amount for line in self.lines.filter(
                nature=BudgetLine.Nature.EXPENSE
            )),
            Decimal("0.00"),
        )

    @property
    def forecast_balance(self):
        return (
            self.total_income_forecast
            - self.total_expense_forecast
        )

    @property
    def actual_balance(self):
        return (
            self.total_income_realized
            - self.total_expense_paid
        )

    def __str__(self):
        return f"{self.name} - {self.fiscal_year}"


# ============================================================
# 2. LIGNES BUDGÉTAIRES
# ============================================================

class BudgetLine(models.Model):

    class Nature(models.TextChoices):
        INCOME = "INCOME", "Recette"
        EXPENSE = "EXPENSE", "Dépense"

    budget = models.ForeignKey(
        Budget,
        on_delete=models.CASCADE,
        related_name="lines",
    )

    nature = models.CharField(
        max_length=10,
        choices=Nature.choices,
        default=Nature.EXPENSE,
    )

    category = models.CharField(max_length=120)

    description = models.CharField(
        max_length=200,
        blank=True,
    )

    initial_amount = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )

    revised_amount = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )

    # Anciens champs conservés temporairement
    # pour préserver les données existantes.
    # Les calculs réels utilisent désormais Finance.

    committed_amount = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=Decimal("0.00"),
        editable=False,
    )

    paid_amount = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=Decimal("0.00"),
        editable=False,
    )

    created_at = models.DateTimeField(default=timezone.now)

    updated_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["nature", "category"]

    def clean(self):
        errors = {}

        if self.initial_amount is not None:
            if self.initial_amount < 0:
                errors["initial_amount"] = (
                    "Le montant initial ne peut pas être négatif."
                )

        if self.revised_amount is not None:
            if self.revised_amount < 0:
                errors["revised_amount"] = (
                    "Le montant révisé ne peut pas être négatif."
                )

        if self.initial_amount and self.revised_amount:
            if self.revised_amount < 0:
                errors["revised_amount"] = (
                    "Le montant révisé doit être positif."
                )

        if self.budget_id:
            if self.budget.status == Budget.Status.CLOSED:
                errors["budget"] = (
                    "Impossible de modifier une ligne "
                    "d'un budget clôturé."
                )

        if errors:
            raise ValidationError(errors)

    # --------------------------------------------------------
    # CALCUL DES ENGAGEMENTS
    # --------------------------------------------------------

    @property
    def calculated_committed_amount(self):

        if self.nature != self.Nature.EXPENSE:
            return Decimal("0.00")

        approved_requests = self.expense_requests.filter(
            status__in=["APPROVED", "PAID"]
        ).aggregate(
            total=Coalesce(
                Sum("amount"),
                Decimal("0.00"),
            )
        )["total"]

        # Les décaissements directs sont ajoutés,
        # mais pas ceux déjà rattachés à une demande.
        direct_expenses = self.cash_expenses.filter(
            status="COMPLETED",
            expense_request__isnull=True,
        ).aggregate(
            total=Coalesce(
                Sum("amount"),
                Decimal("0.00"),
            )
        )["total"]

        return approved_requests + direct_expenses

    # --------------------------------------------------------
    # CALCUL DES PAIEMENTS
    # --------------------------------------------------------

    @property
    def calculated_paid_amount(self):

        if self.nature != self.Nature.EXPENSE:
            return Decimal("0.00")

        return self.cash_expenses.filter(
            status="COMPLETED"
        ).aggregate(
            total=Coalesce(
                Sum("amount"),
                Decimal("0.00"),
            )
        )["total"]

    # --------------------------------------------------------
    # CALCUL DES RECETTES
    # --------------------------------------------------------

    @property
    def realized_amount(self):

        if self.nature != self.Nature.INCOME:
            return Decimal("0.00")

        return self.receipts.filter(
            status="COMPLETED"
        ).aggregate(
            total=Coalesce(
                Sum("amount"),
                Decimal("0.00"),
            )
        )["total"]

    # --------------------------------------------------------
    # DISPONIBLE
    # --------------------------------------------------------

    @property
    def available_amount(self):

        if self.nature == self.Nature.INCOME:
            return (
                self.revised_amount
                - self.realized_amount
            )

        return (
            self.revised_amount
            - self.calculated_committed_amount
        )

    # --------------------------------------------------------
    # TAUX D'EXÉCUTION
    # --------------------------------------------------------

    @property
    def execution_rate(self):

        if self.revised_amount == 0:
            return Decimal("0.00")

        if self.nature == self.Nature.INCOME:
            amount = self.realized_amount
        else:
            amount = self.calculated_paid_amount

        return (
            amount / self.revised_amount
        ) * Decimal("100")

    @property
    def commitment_rate(self):

        if self.nature != self.Nature.EXPENSE:
            return Decimal("0.00")

        if self.revised_amount == 0:
            return Decimal("0.00")

        return (
            self.calculated_committed_amount
            / self.revised_amount
        ) * Decimal("100")

    def __str__(self):
        return f"{self.category} - {self.budget.name}"
