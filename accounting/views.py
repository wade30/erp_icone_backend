
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from users.permissions import (
    ERPModulePermission,
    ServiceScopedQuerysetMixin,
)

from .models import (
    Account,
    Journal,
    AccountingEntry,
    EntryLine,
)

from .serializers import (
    AccountSerializer,
    JournalSerializer,
    AccountingEntrySerializer,
    EntryLineSerializer,
)


# ============================================================
# 1. PLAN COMPTABLE
# ============================================================

class AccountViewSet(
    ServiceScopedQuerysetMixin,
    viewsets.ModelViewSet
):
    queryset = Account.objects.all().order_by("code")

    serializer_class = AccountSerializer

    permission_classes = [
        IsAuthenticated,
        ERPModulePermission,
    ]

    permission_module = "accounting"

    # Les comptes sont communs à toute l'organisation.
    permission_shared_data = True


# ============================================================
# 2. JOURNAUX COMPTABLES
# ============================================================

class JournalViewSet(
    ServiceScopedQuerysetMixin,
    viewsets.ModelViewSet
):
    queryset = Journal.objects.all().order_by("code")

    serializer_class = JournalSerializer

    permission_classes = [
        IsAuthenticated,
        ERPModulePermission,
    ]

    permission_module = "accounting"

    # Les journaux sont communs à toute l'organisation.
    permission_shared_data = True


# ============================================================
# 3. ÉCRITURES COMPTABLES
# ============================================================

class AccountingEntryViewSet(
    ServiceScopedQuerysetMixin,
    viewsets.ReadOnlyModelViewSet
):
    queryset = (
        AccountingEntry.objects
        .select_related(
            "journal",
            "created_by",
            "receipt",
            "cash_expense",
        )
        .prefetch_related(
            "lines",
            "lines__account",
        )
        .all()
        .order_by("-date", "-created_at")
    )

    serializer_class = AccountingEntrySerializer

    permission_classes = [
        IsAuthenticated,
        ERPModulePermission,
    ]

    permission_module = "accounting"

    # Une écriture est visible selon les services
    # associés à ses lignes comptables.
    permission_service_field = "lines__service"

    def get_queryset(self):
        return super().get_queryset().distinct()


# ============================================================
# 4. LIGNES D'ÉCRITURES COMPTABLES
# ============================================================

class EntryLineViewSet(
    ServiceScopedQuerysetMixin,
    viewsets.ReadOnlyModelViewSet
):
    queryset = (
        EntryLine.objects
        .select_related(
            "entry",
            "entry__journal",
            "account",
        )
        .all()
        .order_by("entry__date", "entry__reference", "id")
    )

    serializer_class = EntryLineSerializer

    permission_classes = [
        IsAuthenticated,
        ERPModulePermission,
    ]

    permission_module = "accounting"

    permission_service_field = "service"
