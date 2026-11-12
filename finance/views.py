from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.utils import timezone

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError, PermissionDenied
from rest_framework.response import Response

from users.permissions import (
    ERPModulePermission,
    ServiceScopedQuerysetMixin,
)

from accounting.services import (
    post_receipt,
    post_cash_expense,
)

from .models import (
    BankAccount,
    Receipt,
    CashExpense,
    ExpenseRequest,
)

from .serializers import (
    BankAccountSerializer,
    ReceiptSerializer,
    CashExpenseSerializer,
    ExpenseRequestSerializer,
)


# ============================================================
# 1. CONSTANTES ET FONCTIONS COMMUNES
# ============================================================

APPROVAL_ROLES = {
    "FINANCE",
    "DIRECTOR",
    "PDG",
    "SERVICE_MANAGER",
}

PAYMENT_ROLES = {
    "FINANCE",
}

DIRECT_EXPENSE_ROLES = {
    "FINANCE",
}

FINANCIAL_OPERATION_ROLES = {
    "FINANCE",
    "DIRECTOR",
    "PDG",
}

OPERATIONAL_ROLES = {
    "STAFF",
    "SERVICE_MANAGER",
}


def get_user_role(user):
    role = getattr(user, "role", None)

    if hasattr(role, "value"):
        role = role.value

    return str(role or "").upper()


def get_user_service(user):
    service = getattr(user, "service", None)

    if hasattr(service, "code"):
        service = service.code

    if hasattr(service, "value"):
        service = service.value

    return str(service or "").upper()


def require_roles(user, allowed_roles, message):
    if get_user_role(user) not in allowed_roles:
        raise PermissionDenied(message)


def require_approval(user):
    require_roles(
        user,
        APPROVAL_ROLES,
        "Vous n'êtes pas autorisé à approuver ou rejeter cette demande.",
    )


def require_payment(user):
    require_roles(
        user,
        PAYMENT_ROLES,
        "Seul le service financier peut confirmer un paiement.",
    )


def require_direct_expense(user):
    require_roles(
        user,
        DIRECT_EXPENSE_ROLES,
        "Seul le service financier peut gérer un décaissement direct.",
    )


def require_financial_operation(user):
    require_roles(
        user,
        FINANCIAL_OPERATION_ROLES,
        "Vous n'êtes pas autorisé à effectuer cette opération financière.",
    )


def validate_completion(serializer, instance):
    validator = getattr(
        serializer,
        "validate_for_completion",
        None,
    )

    if not callable(validator):
        raise ValidationError({
            "detail": (
                "La méthode validate_for_completion() "
                "est absente du serializer."
            )
        })

    validator(instance)


def post_accounting_operation(post_operation, operation, user):
    try:
        return post_operation(operation, user)
    except DjangoValidationError as exc:
        detail = (
            exc.message_dict
            if hasattr(exc, "message_dict")
            else {"detail": exc.messages}
        )
        raise ValidationError(detail) from exc


def accounting_response(entry):
    return {
        "accounting_entry_reference": entry.reference,
        "accounting_status": entry.status,
    }


def get_locked_object(view, pk):
    """
    Récupère l'objet à travers le queryset autorisé,
    puis verrouille sa ligne en base.

    Le verrouillage évite les doubles traitements simultanés.
    """

    obj = view.get_object()

    locked_obj = (
        obj.__class__._default_manager
        .select_for_update()
        .get(pk=obj.pk)
    )

    view.check_object_permissions(
        view.request,
        locked_obj,
    )

    return locked_obj


# ============================================================
# 2. COMPTES BANCAIRES
# ============================================================

class BankAccountViewSet(viewsets.ModelViewSet):

    queryset = BankAccount.objects.all().order_by("name")

    serializer_class = BankAccountSerializer

    permission_classes = [
        IsAuthenticated,
        ERPModulePermission,
    ]

    permission_module = "finance"

    def get_queryset(self):
        queryset = super().get_queryset()

        if self.request.query_params.get("is_active") == "true":
            return queryset.filter(is_active=True)

        return queryset

    def perform_create(self, serializer):
        require_financial_operation(self.request.user)
        serializer.save()

    def perform_update(self, serializer):
        require_financial_operation(self.request.user)
        serializer.save()

    def perform_destroy(self, instance):
        require_financial_operation(self.request.user)

        if instance.balance != 0:
            raise ValidationError({
                "detail": (
                    "Impossible de supprimer un compte bancaire "
                    "dont le solde est différent de zéro."
                )
            })

        super().perform_destroy(instance)


# ============================================================
# 3. ENCAISSEMENTS
# ============================================================

class ReceiptViewSet(
    ServiceScopedQuerysetMixin,
    viewsets.ModelViewSet,
):

    queryset = Receipt.objects.select_related(
        "bank_account",
        "budget_line",
        "created_by",
    ).all()

    serializer_class = ReceiptSerializer

    permission_classes = [
        IsAuthenticated,
        ERPModulePermission,
    ]

    permission_module = "finance"
    permission_service_field = "service"

    @transaction.atomic
    def perform_create(self, serializer):
        require_financial_operation(self.request.user)

        receipt = serializer.save(
            created_by=self.request.user,
        )

        required_fields = {
            "date",
            "description",
            "service",
            "amount",
            "payment_method",
        }
        if (
            get_user_role(self.request.user) == "FINANCE"
            and required_fields.issubset(serializer.validated_data)
        ):
            validate_completion(serializer, receipt)
            receipt.status = Receipt.Status.COMPLETED
            receipt.validated = True
            receipt.save(
                update_fields=[
                    "status",
                    "validated",
                ]
            )
            post_accounting_operation(
                post_receipt,
                receipt,
                self.request.user,
            )

    def perform_update(self, serializer):
        require_financial_operation(self.request.user)

        if serializer.instance.status != Receipt.Status.DRAFT:
            raise ValidationError({
                "detail": (
                    "Un encaissement enregistré ne peut plus "
                    "être modifié."
                )
            })

        serializer.save()

    def perform_destroy(self, instance):
        require_financial_operation(self.request.user)

        if instance.status != Receipt.Status.DRAFT:
            raise ValidationError({
                "detail": (
                    "Seul un encaissement en brouillon "
                    "peut être supprimé."
                )
            })

        super().perform_destroy(instance)

    # --------------------------------------------------------
    # CONFIRMER UN ENCAISSEMENT
    # --------------------------------------------------------

    @action(
        detail=True,
        methods=["post"],
        url_path="complete",
    )
    @transaction.atomic
    def complete(self, request, pk=None):

        require_financial_operation(request.user)

        receipt = get_locked_object(self, pk)

        if receipt.status != Receipt.Status.DRAFT:
            raise ValidationError({
                "detail": (
                    "Cet encaissement a déjà été enregistré."
                )
            })

        serializer = self.get_serializer(receipt)

        validate_completion(
            serializer,
            receipt,
        )

        receipt.status = Receipt.Status.COMPLETED
        receipt.validated = True

        receipt.save(
            update_fields=[
                "status",
                "validated",
            ]
        )

        # Comptabilisation automatique.
        # IMPORTANT : transmettre l'objet Receipt,
        # et non receipt.pk.
        entry = post_accounting_operation(
            post_receipt,
            receipt,
            request.user,
        )

        return Response(
            {
                "message": "Encaissement enregistré et comptabilisé.",
                "receipt": self.get_serializer(receipt).data,
                "accounting": accounting_response(entry),
            },
            status=status.HTTP_200_OK,
        )


# ============================================================
# 4. DÉCAISSEMENTS DIRECTS
# ============================================================

class CashExpenseViewSet(
    ServiceScopedQuerysetMixin,
    viewsets.ModelViewSet,
):

    queryset = CashExpense.objects.select_related(
        "bank_account",
        "budget_line",
        "expense_request",
        "recorded_by",
    ).all()

    serializer_class = CashExpenseSerializer

    permission_classes = [
        IsAuthenticated,
        ERPModulePermission,
    ]

    permission_module = "finance"
    permission_service_field = "service"

    @transaction.atomic
    def perform_create(self, serializer):

        require_direct_expense(self.request.user)

        if serializer.validated_data.get("expense_request"):
            raise ValidationError({
                "expense_request": (
                    "Un décaissement direct ne peut pas être "
                    "associé manuellement à une demande."
                )
            })

        expense = serializer.save(
            recorded_by=self.request.user,
        )

        required_fields = {
            "date",
            "service",
            "category",
            "description",
            "amount",
            "payment_method",
        }
        if required_fields.issubset(serializer.validated_data):
            if not expense.description.strip():
                raise ValidationError({
                    "description": (
                        "La justification du décaissement direct "
                        "est obligatoire."
                    )
                })

            validate_completion(serializer, expense)
            expense.status = CashExpense.Status.COMPLETED
            expense.save(update_fields=["status"])
            post_accounting_operation(
                post_cash_expense,
                expense,
                self.request.user,
            )

    def perform_update(self, serializer):

        require_direct_expense(self.request.user)

        expense = serializer.instance

        if expense.status != CashExpense.Status.DRAFT:
            raise ValidationError({
                "detail": (
                    "Un décaissement enregistré ne peut plus "
                    "être modifié."
                )
            })

        if expense.expense_request_id:
            raise ValidationError({
                "detail": (
                    "Un décaissement issu d'une demande approuvée "
                    "ne peut pas être modifié directement."
                )
            })

        serializer.save()

    def perform_destroy(self, instance):

        require_direct_expense(self.request.user)

        if instance.status != CashExpense.Status.DRAFT:
            raise ValidationError({
                "detail": (
                    "Seul un décaissement en brouillon "
                    "peut être supprimé."
                )
            })

        if instance.expense_request_id:
            raise ValidationError({
                "detail": (
                    "Un décaissement lié à une demande "
                    "ne peut pas être supprimé directement."
                )
            })

        super().perform_destroy(instance)

    # --------------------------------------------------------
    # CONFIRMER UN DÉCAISSEMENT DIRECT
    # --------------------------------------------------------

    @action(
        detail=True,
        methods=["post"],
        url_path="complete",
    )
    @transaction.atomic
    def complete(self, request, pk=None):

        require_direct_expense(request.user)

        expense = get_locked_object(self, pk)

        if expense.status != CashExpense.Status.DRAFT:
            raise ValidationError({
                "detail": (
                    "Ce décaissement a déjà été enregistré."
                )
            })

        if expense.expense_request_id:
            raise ValidationError({
                "detail": (
                    "Ce décaissement provient d'une demande. "
                    "Utilisez le processus de paiement de la demande."
                )
            })

        serializer = self.get_serializer(expense)

        validate_completion(
            serializer,
            expense,
        )

        expense.status = CashExpense.Status.COMPLETED

        expense.save(
            update_fields=["status"]
        )

        # Comptabilisation automatique.
        # IMPORTANT : transmettre l'objet CashExpense,
        # et non expense.pk.
        entry = post_accounting_operation(
            post_cash_expense,
            expense,
            request.user,
        )

        return Response(
            {
                "message": "Décaissement enregistré et comptabilisé.",
                "cash_expense": self.get_serializer(expense).data,
                "accounting": accounting_response(entry),
            },
            status=status.HTTP_200_OK,
        )


# ============================================================
# 5. DEMANDES DE DÉPENSES
# ============================================================

class ExpenseRequestViewSet(
    ServiceScopedQuerysetMixin,
    viewsets.ModelViewSet,
):

    queryset = ExpenseRequest.objects.select_related(
        "budget_line",
        "requested_by",
        "approved_by",
        "rejected_by",
        "paid_by",
    ).order_by("-created_at", "-pk")

    serializer_class = ExpenseRequestSerializer

    permission_classes = [
        IsAuthenticated,
        ERPModulePermission,
    ]

    permission_module = "finance"
    permission_service_field = "service"

    permission_operational_request = True
    permission_role_actions = {
        "SERVICE_MANAGER": {"read", "approve"},
        "STAFF": {"read"},
    }

    # --------------------------------------------------------
    # CRÉER UNE DEMANDE
    # --------------------------------------------------------

    def perform_create(self, serializer):

        user = self.request.user

        require_roles(
            user,
            OPERATIONAL_ROLES,
            "Seuls les collaborateurs et responsables "
            "opérationnels peuvent créer une demande.",
        )

        service = get_user_service(user)

        if not service or service == "GENERAL":
            raise ValidationError({
                "service": (
                    "Votre compte doit être associé à un service "
                    "opérationnel."
                )
            })

        serializer.save(
            service=service,
            requested_by=user,
            status=ExpenseRequest.Status.DRAFT,
        )

    # --------------------------------------------------------
    # MODIFIER UNE DEMANDE
    # --------------------------------------------------------

    def perform_update(self, serializer):

        expense_request = serializer.instance
        user = self.request.user

        if expense_request.status != ExpenseRequest.Status.DRAFT:
            raise ValidationError({
                "detail": (
                    "Seule une demande en brouillon peut être modifiée."
                )
            })

        if expense_request.requested_by_id != user.id:
            raise PermissionDenied(
                "Vous ne pouvez modifier que vos propres demandes."
            )

        if expense_request.service != get_user_service(user):
            raise PermissionDenied(
                "Vous ne pouvez modifier que les demandes de votre service."
            )

        serializer.save()

    # --------------------------------------------------------
    # SUPPRIMER UNE DEMANDE
    # --------------------------------------------------------

    def perform_destroy(self, instance):

        user = self.request.user

        if instance.status != ExpenseRequest.Status.DRAFT:
            raise ValidationError({
                "detail": (
                    "Seule une demande en brouillon peut être supprimée."
                )
            })

        if instance.requested_by_id != user.id:
            raise PermissionDenied(
                "Vous ne pouvez supprimer que vos propres demandes."
            )

        if instance.service != get_user_service(user):
            raise PermissionDenied(
                "Vous ne pouvez supprimer que les demandes de votre service."
            )

        super().perform_destroy(instance)

    # --------------------------------------------------------
    # SOUMETTRE UNE DEMANDE
    # --------------------------------------------------------

    @action(
        detail=True,
        methods=["post"],
        url_path="submit",
    )
    @transaction.atomic
    def submit(self, request, pk=None):

        expense_request = get_locked_object(self, pk)

        require_roles(
            request.user,
            OPERATIONAL_ROLES,
            "Seuls les services opérationnels peuvent soumettre une demande.",
        )

        if expense_request.requested_by_id != request.user.id:
            raise PermissionDenied(
                "Vous ne pouvez soumettre que vos propres demandes."
            )

        if expense_request.service != get_user_service(request.user):
            raise PermissionDenied(
                "Vous ne pouvez soumettre que les demandes de votre service."
            )

        if expense_request.status != ExpenseRequest.Status.DRAFT:
            raise ValidationError({
                "detail": (
                    "Seule une demande en brouillon peut être soumise."
                )
            })

        serializer = self.get_serializer(expense_request)

        validate_completion(
            serializer,
            expense_request,
        )

        expense_request.status = ExpenseRequest.Status.SUBMITTED

        expense_request.save(
            update_fields=["status"]
        )

        return Response(
            {
                "message": "Demande soumise au service financier.",
                "expense_request": self.get_serializer(
                    expense_request
                ).data,
            },
            status=status.HTTP_200_OK,
        )

    # --------------------------------------------------------
    # APPROUVER UNE DEMANDE
    # --------------------------------------------------------

    @action(
        detail=True,
        methods=["post"],
        url_path="approve",
    )
    @transaction.atomic
    def approve(self, request, pk=None):

        require_approval(request.user)

        expense_request = get_locked_object(self, pk)
        self.ensure_service_manager_owns_request(
            request.user,
            expense_request,
        )

        if expense_request.status != ExpenseRequest.Status.SUBMITTED:
            raise ValidationError({
                "detail": (
                    "Seule une demande soumise peut être approuvée."
                )
            })

        serializer = self.get_serializer(expense_request)

        validate_completion(
            serializer,
            expense_request,
        )

        # TODO :
        # Ajouter le contrôle du budget disponible
        # avant l'approbation de la demande.

        expense_request.status = ExpenseRequest.Status.APPROVED
        expense_request.approved_by = request.user
        expense_request.approved_at = timezone.now()

        expense_request.save(
            update_fields=[
                "status",
                "approved_by",
                "approved_at",
            ]
        )

        return Response(
            {
                "message": "Demande approuvée. Elle est prête à être payée.",
                "expense_request": self.get_serializer(
                    expense_request
                ).data,
            },
            status=status.HTTP_200_OK,
        )

    # --------------------------------------------------------
    # REJETER UNE DEMANDE
    # --------------------------------------------------------

    @action(
        detail=True,
        methods=["post"],
        url_path="reject",
    )
    @transaction.atomic
    def reject(self, request, pk=None):

        require_approval(request.user)

        expense_request = get_locked_object(self, pk)
        self.ensure_service_manager_owns_request(
            request.user,
            expense_request,
        )

        if expense_request.status != ExpenseRequest.Status.SUBMITTED:
            raise ValidationError({
                "detail": (
                    "Seule une demande soumise peut être rejetée."
                )
            })

        rejection_reason = str(
            request.data.get("rejection_reason", "")
        ).strip()

        if not rejection_reason:
            raise ValidationError({
                "rejection_reason": (
                    "Le motif du rejet est obligatoire."
                )
            })

        expense_request.status = ExpenseRequest.Status.REJECTED
        expense_request.rejected_by = request.user
        expense_request.rejected_at = timezone.now()
        expense_request.rejection_reason = rejection_reason

        expense_request.save(
            update_fields=[
                "status",
                "rejected_by",
                "rejected_at",
                "rejection_reason",
            ]
        )

        return Response(
            {
                "message": "Demande rejetée.",
                "expense_request": self.get_serializer(
                    expense_request
                ).data,
            },
            status=status.HTTP_200_OK,
        )

    @staticmethod
    def ensure_service_manager_owns_request(user, expense_request):
        if (
            get_user_role(user) == "SERVICE_MANAGER"
            and expense_request.service != get_user_service(user)
        ):
            raise PermissionDenied(
                "Vous ne pouvez traiter que les demandes de votre service."
            )

    # --------------------------------------------------------
    # PAYER UNE DEMANDE APPROUVÉE
    # --------------------------------------------------------

    @action(
        detail=True,
        methods=["post"],
        url_path="pay",
    )
    @transaction.atomic
    def pay(self, request, pk=None):

        require_payment(request.user)

        expense_request = get_locked_object(self, pk)

        if expense_request.status != ExpenseRequest.Status.APPROVED:
            raise ValidationError({
                "detail": (
                    "Seule une demande approuvée peut être payée."
                )
            })

        if CashExpense.objects.filter(
            expense_request=expense_request
        ).exists():
            raise ValidationError({
                "detail": (
                    "Un décaissement existe déjà pour cette demande."
                )
            })

        # Les données financières proviennent de la demande approuvée.
        # La Finance fournit uniquement les informations de paiement.

        payment_method = request.data.get("payment_method")
        if not payment_method:
            raise ValidationError({
                "payment_method": (
                    "Le mode de paiement est obligatoire."
                )
            })

        payment_data = {
            "date": (
                request.data.get("date")
                or timezone.localdate()
            ),
            "service": expense_request.service,
            "category": expense_request.category,
            "description": expense_request.description,
            "supplier": expense_request.supplier,
            "amount": expense_request.amount,
            "payment_method": payment_method,
            "external_payment_reference": (
                request.data.get("external_payment_reference", "")
            ),
            "budget_line": expense_request.budget_line_id,
        }
        bank_account_id = request.data.get("bank_account")
        if bank_account_id:
            payment_data["bank_account"] = bank_account_id

        payment_serializer = CashExpenseSerializer(
            data=payment_data,
            context=self.get_serializer_context(),
        )

        payment_serializer.is_valid(
            raise_exception=True
        )

        # Création du décaissement lié à la demande.
        cash_expense = payment_serializer.save(
            recorded_by=request.user,
            expense_request=expense_request,
        )

        # Validation complète avant confirmation du paiement.
        validate_completion(
            payment_serializer,
            cash_expense,
        )

        cash_expense.status = CashExpense.Status.COMPLETED

        cash_expense.save(
            update_fields=["status"]
        )

        # Comptabilisation automatique.
        # IMPORTANT : transmettre l'objet CashExpense,
        # et non cash_expense.pk.
        entry = post_accounting_operation(
            post_cash_expense,
            cash_expense,
            request.user,
        )

        # La demande devient payée uniquement après
        # la réussite du décaissement et de la comptabilisation.
        expense_request.status = ExpenseRequest.Status.PAID
        expense_request.paid_by = request.user
        expense_request.paid_at = timezone.localdate()

        expense_request.save(
            update_fields=[
                "status",
                "paid_by",
                "paid_at",
            ]
        )

        return Response(
            {
                "message": "Paiement effectué et comptabilisé avec succès.",
                "expense_request": self.get_serializer(
                    expense_request
                ).data,
                "cash_expense": CashExpenseSerializer(
                    cash_expense,
                    context=self.get_serializer_context(),
                ).data,
                "accounting": accounting_response(entry),
            },
            status=status.HTTP_201_CREATED,
        )
