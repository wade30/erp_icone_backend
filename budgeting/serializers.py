
from django.core.exceptions import ValidationError as DjangoValidationError

from rest_framework import serializers

from .models import Budget, BudgetLine


# ============================================================
# 1. FONCTIONS COMMUNES
# ============================================================

def get_user_service(user):
    """Retourne le code du service de l'utilisateur."""

    service = getattr(user, "service", None)

    if hasattr(service, "code"):
        service = service.code

    if hasattr(service, "value"):
        service = service.value

    return str(service or "").upper()


def validate_model_clean(instance):
    """Exécute la validation métier du modèle."""

    try:
        instance.clean()
    except DjangoValidationError as exc:
        errors = getattr(exc, "message_dict", None)

        if errors is None:
            errors = exc.messages

        raise serializers.ValidationError(errors)


def validate_service_access(user, service):
    """Vérifie que l'utilisateur accède au budget de son service."""

    user_service = get_user_service(user)

    if not user_service:
        raise serializers.ValidationError({
            "service": "Votre compte n'est associé à aucun service."
        })

    if user_service != "GENERAL" and service != user_service:
        raise serializers.ValidationError({
            "service": (
                "Vous ne pouvez gérer que les budgets "
                "de votre propre service."
            )
        })


# ============================================================
# 2. LIGNES BUDGÉTAIRES
# ============================================================

class BudgetLineSerializer(serializers.ModelSerializer):

    available_amount = serializers.ReadOnlyField()
    execution_rate = serializers.ReadOnlyField()
    commitment_rate = serializers.ReadOnlyField()

    realized_amount = serializers.ReadOnlyField()
    calculated_committed_amount = serializers.ReadOnlyField()
    calculated_paid_amount = serializers.ReadOnlyField()

    class Meta:
        model = BudgetLine
        fields = "__all__"

        read_only_fields = [
            "id",
            "committed_amount",
            "paid_amount",
            "created_at",
            "updated_at",
            "available_amount",
            "execution_rate",
            "commitment_rate",
            "realized_amount",
            "calculated_committed_amount",
            "calculated_paid_amount",
        ]

    def validate(self, attrs):

        request = self.context.get("request")

        budget = attrs.get(
            "budget",
            getattr(self.instance, "budget", None),
        )

        if not budget:
            raise serializers.ValidationError({
                "budget": "Un budget doit être sélectionné."
            })

        # ----------------------------------------------------
        # CONTRÔLE DU SERVICE
        # ----------------------------------------------------

        if request:
            validate_service_access(
                request.user,
                budget.service,
            )

        # ----------------------------------------------------
        # CONTRÔLE DU STATUT DU BUDGET
        # ----------------------------------------------------

        if budget.status != Budget.Status.DRAFT:
            raise serializers.ValidationError({
                "budget": (
                    "Les lignes budgétaires ne peuvent être "
                    "créées ou modifiées que lorsque le budget "
                    "est en brouillon."
                )
            })

        # ----------------------------------------------------
        # VALIDATION DU MODÈLE
        # ----------------------------------------------------

        candidate = self.instance or BudgetLine()

        for field, value in attrs.items():
            setattr(candidate, field, value)

        validate_model_clean(candidate)

        return attrs


# ============================================================
# 3. BUDGETS
# ============================================================

class BudgetSerializer(serializers.ModelSerializer):

    lines = BudgetLineSerializer(
        many=True,
        read_only=True,
    )

    created_by = serializers.StringRelatedField(
        read_only=True,
    )

    total_income_forecast = serializers.ReadOnlyField()
    total_expense_forecast = serializers.ReadOnlyField()

    total_income_realized = serializers.ReadOnlyField()
    total_expense_paid = serializers.ReadOnlyField()

    forecast_balance = serializers.ReadOnlyField()
    actual_balance = serializers.ReadOnlyField()

    class Meta:
        model = Budget
        fields = "__all__"

        read_only_fields = [
            "id",
            "created_by",
            "created_at",
            "updated_at",
            "status",
            "lines",
            "total_income_forecast",
            "total_expense_forecast",
            "total_income_realized",
            "total_expense_paid",
            "forecast_balance",
            "actual_balance",
        ]

    def validate(self, attrs):

        request = self.context.get("request")

        service = attrs.get(
            "service",
            getattr(self.instance, "service", None),
        )

        # ----------------------------------------------------
        # CONTRÔLE DU SERVICE
        # ----------------------------------------------------

        if request and service:
            validate_service_access(
                request.user,
                service,
            )

        # ----------------------------------------------------
        # CONTRÔLE DU STATUT
        # ----------------------------------------------------

        if self.instance:
            if self.instance.status != Budget.Status.DRAFT:
                raise serializers.ValidationError({
                    "status": (
                        "Seul un budget en brouillon "
                        "peut être modifié."
                    )
                })

        # ----------------------------------------------------
        # VALIDATION DU MODÈLE
        # ----------------------------------------------------

        candidate = self.instance or Budget()

        for field, value in attrs.items():
            setattr(candidate, field, value)

        validate_model_clean(candidate)

        return attrs

    def create(self, validated_data):

        request = self.context.get("request")

        if not request:
            raise serializers.ValidationError({
                "detail": "Utilisateur authentifié requis."
            })

        validated_data["created_by"] = request.user

        # Un nouveau budget commence toujours en brouillon.
        validated_data["status"] = Budget.Status.DRAFT

        return super().create(validated_data)
