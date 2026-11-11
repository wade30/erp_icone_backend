
from decimal import Decimal, InvalidOperation

from rest_framework import serializers

from .models import (
    Account,
    Journal,
    AccountingEntry,
    EntryLine,
)


# ============================================================
# 1. PLAN COMPTABLE
# ============================================================

class AccountSerializer(serializers.ModelSerializer):

    class Meta:
        model = Account
        fields = [
            "id",
            "code",
            "name",
            "account_type",
            "is_active",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
        ]


# ============================================================
# 2. JOURNAUX COMPTABLES
# ============================================================

class JournalSerializer(serializers.ModelSerializer):

    class Meta:
        model = Journal
        fields = [
            "id",
            "code",
            "name",
            "is_active",
        ]

        read_only_fields = ["id"]


# ============================================================
# 3. LIGNES D'ÉCRITURES
# ============================================================

class EntryLineSerializer(serializers.ModelSerializer):

    account_name = serializers.CharField(
        source="account.name",
        read_only=True,
    )

    account_code = serializers.CharField(
        source="account.code",
        read_only=True,
    )

    class Meta:
        model = EntryLine

        fields = [
            "id",
            "entry",
            "account",
            "account_code",
            "account_name",
            "service",
            "description",
            "debit",
            "credit",
        ]

        read_only_fields = [
            "id",
            "entry",
            "account_code",
            "account_name",
        ]

    def validate_account(self, account):
        if not account.is_active:
            raise serializers.ValidationError(
                "Ce compte comptable est inactif."
            )

        return account

    def validate(self, attrs):

        debit = attrs.get(
            "debit",
            getattr(self.instance, "debit", Decimal("0.00")),
        )

        credit = attrs.get(
            "credit",
            getattr(self.instance, "credit", Decimal("0.00")),
        )

        try:
            debit = Decimal(str(debit))
            credit = Decimal(str(credit))
        except (InvalidOperation, TypeError, ValueError):
            raise serializers.ValidationError(
                "Les montants débit et crédit doivent être numériques."
            )

        if not debit.is_finite() or not credit.is_finite():
            raise serializers.ValidationError(
                "Les montants doivent être des nombres valides."
            )

        if debit < 0 or credit < 0:
            raise serializers.ValidationError(
                "Les montants ne peuvent pas être négatifs."
            )

        if debit > 0 and credit > 0:
            raise serializers.ValidationError(
                "Une ligne ne peut pas comporter simultanément "
                "un débit et un crédit."
            )

        if debit == 0 and credit == 0:
            raise serializers.ValidationError(
                "Une ligne doit comporter un débit ou un crédit."
            )

        if self.instance:
            if self.instance.entry.status in [
                AccountingEntry.Status.POSTED,
                AccountingEntry.Status.CANCELLED,
            ]:
                raise serializers.ValidationError(
                    "Impossible de modifier une ligne appartenant "
                    "à une écriture verrouillée."
                )

        return attrs


# ============================================================
# 4. ÉCRITURES COMPTABLES
# ============================================================

class AccountingEntrySerializer(serializers.ModelSerializer):

    lines = EntryLineSerializer(
        many=True,
        read_only=True,
    )

    journal_name = serializers.CharField(
        source="journal.name",
        read_only=True,
    )

    class Meta:
        model = AccountingEntry

        fields = [
            "id",
            "reference",
            "date",
            "journal",
            "journal_name",
            "description",
            "status",
            "receipt",
            "cash_expense",
            "created_by",
            "created_at",
            "lines",
        ]

        read_only_fields = [
            "id",
            "reference",
            "status",
            "receipt",
            "cash_expense",
            "created_by",
            "created_at",
            "lines",
        ]

    def validate_journal(self, journal):
        if not journal.is_active:
            raise serializers.ValidationError(
                "Ce journal comptable est inactif."
            )

        return journal

    def validate(self, attrs):

        if self.instance:
            if self.instance.status in [
                AccountingEntry.Status.POSTED,
                AccountingEntry.Status.CANCELLED,
            ]:
                raise serializers.ValidationError(
                    "Cette écriture est verrouillée et ne peut plus "
                    "être modifiée."
                )

        return attrs
