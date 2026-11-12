
from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError, PermissionDenied
from rest_framework.response import Response

from django.db import transaction

from users.permissions import (
    ERPModulePermission,
    ServiceScopedQuerysetMixin,
)

from .models import Budget, BudgetLine
from .serializers import (
    BudgetSerializer,
    BudgetLineSerializer,
)


# ============================================================
# 1. RÔLES AUTORISÉS
# ============================================================

BUDGET_SUBMISSION_ROLES = {
    "SERVICE_MANAGER",
    "FINANCE",
}

BUDGET_APPROVAL_ROLES = {
    "FINANCE",
    "DIRECTOR",
    "PDG",
}

BUDGET_CLOSING_ROLES = {
    "FINANCE",
    "DIRECTOR",
    "PDG",
}


def get_user_role(user):
    role = getattr(user, "role", None)

    if hasattr(role, "value"):
        role = role.value

    return str(role or "").upper()


def require_role(user, allowed_roles, message):
    if get_user_role(user) not in allowed_roles:
        raise PermissionDenied(message)


# ============================================================
# 2. GESTION DES BUDGETS
# ============================================================

class BudgetViewSet(
    ServiceScopedQuerysetMixin,
    viewsets.ModelViewSet,
):

    queryset = (
        Budget.objects
        .select_related("created_by")
        .prefetch_related("lines")
        .all()
        .order_by("-fiscal_year", "service", "name")
    )

    serializer_class = BudgetSerializer

    permission_classes = [
        IsAuthenticated,
        ERPModulePermission,
    ]

    permission_module = "budgeting"
    permission_service_field = "service"

    # --------------------------------------------------------
    # CRÉATION
    # --------------------------------------------------------

    def perform_create(self, serializer):

        serializer.save(
            created_by=self.request.user,
            status=Budget.Status.DRAFT,
        )

    # --------------------------------------------------------
    # MODIFICATION
    # --------------------------------------------------------

    def perform_update(self, serializer):

        budget = serializer.instance

        if budget.status != Budget.Status.DRAFT:
            raise ValidationError({
                "status": (
                    "Seul un budget en brouillon "
                    "peut être modifié."
                )
            })

        serializer.save()

    # --------------------------------------------------------
    # SUPPRESSION
    # --------------------------------------------------------

    def perform_destroy(self, instance):

        if instance.status != Budget.Status.DRAFT:
            raise ValidationError({
                "status": (
                    "Seul un budget en brouillon "
                    "peut être supprimé."
                )
            })

        instance.delete()

    # --------------------------------------------------------
    # SOUMISSION
    # --------------------------------------------------------

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):

        require_role(
            request.user,
            BUDGET_SUBMISSION_ROLES,
            "Vous n'êtes pas autorisé à soumettre un budget.",
        )

        with transaction.atomic():

            budget = self.get_object()

            budget = (
                Budget.objects
                .select_for_update()
                .get(pk=budget.pk)
            )

            self.check_object_permissions(request, budget)

            if budget.status != Budget.Status.DRAFT:
                raise ValidationError({
                    "status": (
                        "Seul un budget en brouillon "
                        "peut être soumis."
                    )
                })

            if not budget.lines.exists():
                raise ValidationError({
                    "lines": (
                        "Ajoutez au moins une ligne budgétaire "
                        "avant de soumettre le budget."
                    )
                })

            budget.status = Budget.Status.SUBMITTED

            budget.save(update_fields=["status"])

        return Response(
            self.get_serializer(budget).data,
            status=status.HTTP_200_OK,
        )

    # --------------------------------------------------------
    # APPROBATION
    # --------------------------------------------------------

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):

        require_role(
            request.user,
            BUDGET_APPROVAL_ROLES,
            "Vous n'êtes pas autorisé à approuver ce budget.",
        )

        with transaction.atomic():

            budget = self.get_object()

            budget = (
                Budget.objects
                .select_for_update()
                .get(pk=budget.pk)
            )

            self.check_object_permissions(request, budget)

            if budget.status != Budget.Status.SUBMITTED:
                raise ValidationError({
                    "status": (
                        "Seul un budget soumis "
                        "peut être approuvé."
                    )
                })

            if not budget.lines.exists():
                raise ValidationError({
                    "lines": (
                        "Impossible d'approuver un budget "
                        "sans ligne budgétaire."
                    )
                })

            budget.status = Budget.Status.APPROVED

            budget.save(update_fields=["status"])

        return Response(
            self.get_serializer(budget).data,
            status=status.HTTP_200_OK,
        )

    # --------------------------------------------------------
    # CLÔTURE
    # --------------------------------------------------------

    @action(detail=True, methods=["post"])
    def close(self, request, pk=None):

        require_role(
            request.user,
            BUDGET_CLOSING_ROLES,
            "Vous n'êtes pas autorisé à clôturer ce budget.",
        )

        with transaction.atomic():

            budget = self.get_object()

            budget = (
                Budget.objects
                .select_for_update()
                .get(pk=budget.pk)
            )

            self.check_object_permissions(request, budget)

            if budget.status != Budget.Status.APPROVED:
                raise ValidationError({
                    "status": (
                        "Seul un budget approuvé "
                        "peut être clôturé."
                    )
                })

            budget.status = Budget.Status.CLOSED

            budget.save(update_fields=["status"])

        return Response(
            self.get_serializer(budget).data,
            status=status.HTTP_200_OK,
        )


# ============================================================
# 3. GESTION DES LIGNES BUDGÉTAIRES
# ============================================================

class BudgetLineViewSet(
    ServiceScopedQuerysetMixin,
    viewsets.ModelViewSet,
):

    queryset = (
        BudgetLine.objects
        .select_related("budget")
        .all()
        .order_by("budget__fiscal_year", "nature", "category")
    )

    serializer_class = BudgetLineSerializer

    permission_classes = [
        IsAuthenticated,
        ERPModulePermission,
    ]

    permission_module = "budgeting"
    permission_service_field = "budget__service"

    # --------------------------------------------------------
    # SUPPRESSION
    # --------------------------------------------------------

    def perform_destroy(self, instance):

        if instance.budget.status != Budget.Status.DRAFT:
            raise ValidationError({
                "budget": (
                    "Les lignes d'un budget soumis, approuvé "
                    "ou clôturé ne peuvent pas être supprimées."
                )
            })

        instance.delete()
