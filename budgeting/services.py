from decimal import Decimal

from django.db import transaction
from django.core.exceptions import ValidationError

from .models import BudgetLine


@transaction.atomic
def validate_expense_request_budget(expense_request):
    """
    Vérifie le budget avant l'approbation d'une demande.

    Le verrouillage de la ligne budgétaire empêche
    deux approbations simultanées de dépasser le budget.
    """

    if not expense_request.budget_line_id:
        raise ValidationError({
            "budget_line": (
                "Une ligne budgétaire est obligatoire "
                "pour approuver cette demande."
            )
        })

    budget_line = (
        BudgetLine.objects
        .select_for_update()
        .select_related("budget")
        .get(pk=expense_request.budget_line_id)
    )

    budget = budget_line.budget

    # 1. Vérifier la nature de la ligne.

    if budget_line.nature != BudgetLine.Nature.EXPENSE:
        raise ValidationError({
            "budget_line": (
                "Cette ligne budgétaire n'est pas une ligne de dépense."
            )
        })

    # 2. Vérifier le statut du budget.

    if budget.status != budget.Status.APPROVED:
        raise ValidationError({
            "budget": (
                "Seul un budget approuvé peut financer une demande."
            )
        })

    # 3. Vérifier le service.

    if budget.service != expense_request.service:
        raise ValidationError({
            "budget_line": (
                "Cette ligne budgétaire n'appartient pas "
                "au service concerné."
            )
        })

    # 4. Vérifier la période.

    if expense_request.date:
        if not (
            budget.start_date
            <= expense_request.date
            <= budget.end_date
        ):
            raise ValidationError({
                "date": (
                    "La date de la demande est hors "
                    "de la période du budget."
                )
            })

    # 5. Calculer le disponible actualisé.

    available = budget_line.available_amount

    requested_amount = (
        expense_request.amount or Decimal("0.00")
    )

    if requested_amount <= Decimal("0.00"):
        raise ValidationError({
            "amount": "Le montant doit être supérieur à zéro."
        })

    if requested_amount > available:
        raise ValidationError({
            "budget_line": (
                f"Budget insuffisant. "
                f"Disponible : {available} FCFA. "
                f"Demande : {requested_amount} FCFA."
            )
        })

    return budget_line