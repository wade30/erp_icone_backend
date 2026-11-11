
from rest_framework import serializers

from budgeting.models import BudgetLine

from .models import (
    BankAccount,
    CashExpense,
    Receipt,
    ExpenseRequest,
)


# ============================================================
# 0. OUTILS DE VALIDATION
# ============================================================

def get_service_code(user):
    """Retourne le code normalisé du service."""

    service = getattr(user, "service", None)

    if not service:
        return None

    if hasattr(service, "code"):
        service = service.code
    elif hasattr(service, "value"):
        service = service.value

    return str(service).upper()


def validate_budget_line(
    budget_line,
    service,
    expected_nature,
    request=None,
):
    """Vérifie la cohérence entre opération, service et budget."""

    if not budget_line:
        return

    errors = {}
    budget = budget_line.budget

    if budget_line.nature != expected_nature:
        errors["budget_line"] = (
            "La nature de la ligne budgétaire ne correspond pas "
            "à l'opération."
        )

    if service and budget.service != service:
        errors["budget_line"] = (
            "Le service de l'opération ne correspond pas "
            "au service du budget."
        )

    if budget.status == BudgetLine._meta.get_field(
        "budget"
    ).remote_field.model.Status.CLOSED:
        errors["budget_line"] = (
            "Impossible d'utiliser une ligne d'un budget clôturé."
        )

    if request and request.user.is_authenticated:
        user_service = get_service_code(request.user)

        if (
            user_service
            and user_service != "GENERAL"
            and budget.service != user_service
        ):
            errors["budget_line"] = (
                "Vous ne pouvez utiliser que les lignes "
                "budgétaires de votre service."
            )

    if errors:
        raise serializers.ValidationError(errors)


def validate_service_immutability(attrs, instance):
    """Empêche de modifier le service après création."""

    if not instance:
        return

    new_service = attrs.get("service", instance.service)

    if new_service != instance.service:
        raise serializers.ValidationError({
            "service": (
                "Le service d'une opération ne peut plus "
                "être modifié après sa création."
            )
        })


def validate_payment_bank_account(instance, errors):
    """Contrôle la cohérence du compte bancaire et du paiement."""

    if instance.payment_method == Receipt.PaymentMethod.BANK:
        if not instance.bank_account_id:
            errors["bank_account"] = (
                "Un compte bancaire est obligatoire pour un virement."
            )
        elif not instance.bank_account.is_active:
            errors["bank_account"] = (
                "Ce compte bancaire est désactivé."
            )

    elif instance.bank_account_id:
        errors["bank_account"] = (
            "Un compte bancaire ne doit être renseigné "
            "que pour un virement bancaire."
        )


def validate_required_fields(instance, required_fields):
    errors = {}

    for field, message in required_fields.items():
        value = getattr(instance, field, None)

        if value is None or value == "":
            errors[field] = message

    return errors


# ============================================================
# 1. COMPTES BANCAIRES
# ============================================================

class BankAccountSerializer(serializers.ModelSerializer):

    class Meta:
        model = BankAccount
        fields = "__all__"

        read_only_fields = [
            "id",
            "balance",
        ]


# ============================================================
# 2. ENCAISSEMENTS
# ============================================================

class ReceiptSerializer(serializers.ModelSerializer):

    created_by = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Receipt
        fields = "__all__"

        read_only_fields = [
            "id",
            "reference",
            "payment_reference",
            "created_by",
            "validated",
            "status",
            "created_at",
        ]

    def validate_amount(self, value):
        if value is not None and value <= 0:
            raise serializers.ValidationError(
                "Le montant doit être supérieur à zéro."
            )
        return value

    def validate(self, attrs):
        instance = self.instance

        if instance and instance.status != Receipt.Status.DRAFT:
            raise serializers.ValidationError(
                "Un encaissement déjà enregistré ne peut plus "
                "être modifié."
            )

        validate_service_immutability(attrs, instance)

        service = attrs.get(
            "service",
            getattr(instance, "service", None),
        )

        budget_line = attrs.get(
            "budget_line",
            getattr(instance, "budget_line", None),
        )

        validate_budget_line(
            budget_line=budget_line,
            service=service,
            expected_nature=BudgetLine.Nature.INCOME,
            request=self.context.get("request"),
        )

        return attrs

    def create(self, validated_data):
        request = self.context.get("request")

        if request and request.user.is_authenticated:
            validated_data["created_by"] = request.user

        return super().create(validated_data)

    def validate_for_completion(self, instance):
        errors = validate_required_fields(
            instance,
            {
                "date": "La date est obligatoire.",
                "description": "La description est obligatoire.",
                "service": "Le service est obligatoire.",
                "amount": "Le montant est obligatoire.",
                "payment_method": "Le mode de paiement est obligatoire.",
            },
        )

        if instance.amount is not None and instance.amount <= 0:
            errors["amount"] = "Le montant doit être supérieur à zéro."

        validate_payment_bank_account(instance, errors)

        try:
            validate_budget_line(
                budget_line=instance.budget_line,
                service=instance.service,
                expected_nature=BudgetLine.Nature.INCOME,
                request=self.context.get("request"),
            )
        except serializers.ValidationError as exc:
            errors.update(exc.detail)

        if errors:
            raise serializers.ValidationError(errors)

        return instance


# ============================================================
# 3. DÉCAISSEMENTS
# ============================================================

class CashExpenseSerializer(serializers.ModelSerializer):

    recorded_by = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = CashExpense
        fields = "__all__"

        read_only_fields = [
            "id",
            "reference",
            "payment_reference",
            "recorded_by",
            "expense_request",
            "status",
            "created_at",
        ]

    def validate_amount(self, value):
        if value is not None and value <= 0:
            raise serializers.ValidationError(
                "Le montant doit être supérieur à zéro."
            )
        return value

    def validate(self, attrs):
        instance = self.instance

        if instance and instance.status != CashExpense.Status.DRAFT:
            raise serializers.ValidationError(
                "Un décaissement déjà enregistré ne peut plus "
                "être modifié."
            )

        validate_service_immutability(attrs, instance)

        service = attrs.get(
            "service",
            getattr(instance, "service", None),
        )

        budget_line = attrs.get(
            "budget_line",
            getattr(instance, "budget_line", None),
        )

        validate_budget_line(
            budget_line=budget_line,
            service=service,
            expected_nature=BudgetLine.Nature.EXPENSE,
            request=self.context.get("request"),
        )

        expense_request = (
            getattr(instance, "expense_request", None)
            if instance else None
        )

        if expense_request:
            if expense_request.status != ExpenseRequest.Status.APPROVED:
                raise serializers.ValidationError({
                    "expense_request": (
                        "La demande liée doit être approuvée "
                        "avant le paiement."
                    )
                })

            if expense_request.service != service:
                raise serializers.ValidationError({
                    "service": "Le service ne correspond pas à la demande."
                })

            amount = attrs.get(
                "amount",
                getattr(instance, "amount", None),
            )

            if expense_request.amount != amount:
                raise serializers.ValidationError({
                    "amount": (
                        "Le montant doit correspondre au montant approuvé."
                    )
                })

            if expense_request.budget_line_id != (
                budget_line.id if budget_line else None
            ):
                raise serializers.ValidationError({
                    "budget_line": (
                        "La ligne budgétaire doit être identique "
                        "à celle de la demande."
                    )
                })

        return attrs

    def create(self, validated_data):
        request = self.context.get("request")

        if request and request.user.is_authenticated:
            validated_data["recorded_by"] = request.user

        return super().create(validated_data)

    def validate_for_completion(self, instance):
        errors = validate_required_fields(
            instance,
            {
                "date": "La date est obligatoire.",
                "service": "Le service est obligatoire.",
                "category": "La catégorie est obligatoire.",
                "description": "La description est obligatoire.",
                "amount": "Le montant est obligatoire.",
                "payment_method": "Le mode de paiement est obligatoire.",
            },
        )

        if instance.amount is not None and instance.amount <= 0:
            errors["amount"] = "Le montant doit être supérieur à zéro."

        validate_payment_bank_account(instance, errors)

        try:
            validate_budget_line(
                budget_line=instance.budget_line,
                service=instance.service,
                expected_nature=BudgetLine.Nature.EXPENSE,
                request=self.context.get("request"),
            )
        except serializers.ValidationError as exc:
            errors.update(exc.detail)

        expense_request = instance.expense_request

        if expense_request:
            if expense_request.status != ExpenseRequest.Status.APPROVED:
                errors["expense_request"] = (
                    "La demande doit être approuvée avant le paiement."
                )

            if expense_request.service != instance.service:
                errors["service"] = (
                    "Le service ne correspond pas à la demande approuvée."
                )

            if expense_request.amount != instance.amount:
                errors["amount"] = (
                    "Le montant ne correspond pas à la demande approuvée."
                )

            if expense_request.budget_line_id != instance.budget_line_id:
                errors["budget_line"] = (
                    "La ligne budgétaire doit être identique "
                    "à celle de la demande."
                )

        if errors:
            raise serializers.ValidationError(errors)

        return instance


# ============================================================
# 4. DEMANDES DE DÉPENSES
# ============================================================

class ExpenseRequestSerializer(serializers.ModelSerializer):

    requested_by = serializers.StringRelatedField(read_only=True)
    requested_by_id = serializers.IntegerField(
        source="requested_by.id",
        read_only=True,
    )
    approved_by = serializers.StringRelatedField(read_only=True)
    rejected_by = serializers.StringRelatedField(read_only=True)
    paid_by = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = ExpenseRequest
        fields = "__all__"

        read_only_fields = [
            "id",
            "reference",
            "requested_by",
            "approved_by",
            "approved_at",
            "rejected_by",
            "rejected_at",
            "rejection_reason",
            "paid_by",
            "paid_at",
            "status",
            "created_at",
        ]

    def validate_amount(self, value):
        if value is not None and value <= 0:
            raise serializers.ValidationError(
                "Le montant doit être supérieur à zéro."
            )
        return value

    def validate(self, attrs):
        instance = self.instance

        if instance and instance.status != ExpenseRequest.Status.DRAFT:
            raise serializers.ValidationError(
                "Seule une demande en brouillon peut être modifiée."
            )

        validate_service_immutability(attrs, instance)

        service = attrs.get(
            "service",
            getattr(instance, "service", None),
        )

        budget_line = attrs.get(
            "budget_line",
            getattr(instance, "budget_line", None),
        )

        validate_budget_line(
            budget_line=budget_line,
            service=service,
            expected_nature=BudgetLine.Nature.EXPENSE,
            request=self.context.get("request"),
        )

        return attrs

    def create(self, validated_data):
        request = self.context.get("request")

        if request and request.user.is_authenticated:
            validated_data["requested_by"] = request.user

        return super().create(validated_data)

    def validate_for_completion(self, instance):
        errors = validate_required_fields(
            instance,
            {
                "date": "La date est obligatoire.",
                "service": "Le service est obligatoire.",
                "category": "La catégorie est obligatoire.",
                "description": "La description est obligatoire.",
                "amount": "Le montant est obligatoire.",
            },
        )

        if instance.amount is not None and instance.amount <= 0:
            errors["amount"] = "Le montant doit être supérieur à zéro."

        try:
            validate_budget_line(
                budget_line=instance.budget_line,
                service=instance.service,
                expected_nature=BudgetLine.Nature.EXPENSE,
                request=self.context.get("request"),
            )
        except serializers.ValidationError as exc:
            errors.update(exc.detail)

        if errors:
            raise serializers.ValidationError(errors)

        return instance
