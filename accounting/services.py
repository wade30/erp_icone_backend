
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction

from finance.models import Receipt, CashExpense

from .models import (
    Account,
    Journal,
    AccountingEntry,
    EntryLine,
)


# ============================================================
# 1. CONFIGURATION COMPTABLE
# ============================================================

def get_accounting_config():
    """
    Récupère la configuration de comptabilisation automatique.
    """
    config = getattr(settings, "ACCOUNTING_AUTOMATION", None)

    if not isinstance(config, dict) or not config:
        raise ValidationError(
            "La configuration ACCOUNTING_AUTOMATION "
            "est absente ou incorrecte dans settings.py."
        )

    return config


# ============================================================
# 2. RÉCUPÉRATION DES COMPTES
# ============================================================

def get_active_account(account_code, description):
    """
    Récupère un compte comptable actif à partir de son code.
    """

    if not account_code:
        raise ValidationError(
            f"Le compte comptable n'est pas configuré : {description}."
        )

    try:
        return Account.objects.get(
            code=str(account_code),
            is_active=True,
        )

    except Account.DoesNotExist:
        raise ValidationError(
            f"Le compte {account_code} ({description}) "
            "n'existe pas ou est inactif."
        )

    except Account.MultipleObjectsReturned:
        raise ValidationError(
            f"Plusieurs comptes possèdent le code {account_code}."
        )


# ============================================================
# 3. RÉCUPÉRATION DES JOURNAUX
# ============================================================

def get_active_journal(journal_code):
    """
    Récupère un journal comptable actif.
    """

    if not journal_code:
        raise ValidationError(
            "Aucun journal comptable n'est configuré "
            "pour ce moyen de paiement."
        )

    try:
        return Journal.objects.get(
            code=str(journal_code),
            is_active=True,
        )

    except Journal.DoesNotExist:
        raise ValidationError(
            f"Le journal {journal_code} n'existe pas ou est inactif."
        )

    except Journal.MultipleObjectsReturned:
        raise ValidationError(
            f"Plusieurs journaux possèdent le code {journal_code}."
        )


def get_journal_for_operation(operation, config):
    """
    Sélectionne le journal selon :
    - le type d'opération ;
    - le moyen de paiement.
    """

    payment_method = operation.payment_method

    if not payment_method:
        raise ValidationError(
            "Le moyen de paiement est obligatoire."
        )

    if isinstance(operation, Receipt):
        journal_mapping = config.get(
            "receipt_journal_codes",
            {},
        )

    elif isinstance(operation, CashExpense):
        journal_mapping = config.get(
            "expense_journal_codes",
            {},
        )

    else:
        raise ValidationError(
            "Type d'opération financière non pris en charge."
        )

    journal_code = journal_mapping.get(payment_method)

    if not journal_code:
        raise ValidationError(
            f"Aucun journal n'est configuré pour "
            f"le moyen de paiement {payment_method}."
        )

    return get_active_journal(journal_code)


# ============================================================
# 4. VALIDATION DES OPÉRATIONS FINANCIÈRES
# ============================================================

def validate_financial_operation(operation):
    """
    Vérifie les informations obligatoires avant comptabilisation.
    """

    if not operation.date:
        raise ValidationError(
            "La date de l'opération est obligatoire."
        )

    if not operation.service:
        raise ValidationError(
            "Le service concerné est obligatoire."
        )

    if operation.amount is None:
        raise ValidationError(
            "Le montant de l'opération est obligatoire."
        )

    try:
        amount = Decimal(str(operation.amount))
    except (InvalidOperation, TypeError, ValueError):
        raise ValidationError(
            "Le montant de l'opération est invalide."
        )

    if not amount.is_finite() or amount <= Decimal("0.00"):
        raise ValidationError(
            "Le montant doit être strictement supérieur à zéro."
        )

    return amount


# ============================================================
# 5. COMPTE DE TRÉSORERIE
# ============================================================

def get_treasury_account(operation, config):
    """
    Détermine le compte de trésorerie selon le moyen de paiement.
    """

    payment_method = operation.payment_method

    if not payment_method:
        raise ValidationError(
            "Le moyen de paiement est obligatoire."
        )

    # Paiement ou encaissement par banque
    if payment_method == "BANK":

        bank_account = operation.bank_account

        if not bank_account:
            raise ValidationError(
                "Un compte bancaire doit être sélectionné."
            )

        if not bank_account.is_active:
            raise ValidationError(
                "Le compte bancaire sélectionné est inactif."
            )

        bank_accounts = config.get(
            "bank_account_codes",
            {},
        )

        account_code = bank_accounts.get(
            str(operation.bank_account_id)
        )

        if not account_code:
            raise ValidationError(
                "Aucun compte comptable n'est associé "
                "à ce compte bancaire dans settings.py."
            )

        return get_active_account(
            account_code,
            "Compte bancaire",
        )

    # Caisse, Wave, Orange Money et autres moyens
    payment_accounts = config.get(
        "payment_account_codes",
        {},
    )

    account_code = payment_accounts.get(payment_method)

    return get_active_account(
        account_code,
        f"Trésorerie - {payment_method}",
    )


# ============================================================
# 6. COMPTE DE PRODUITS
# ============================================================

def get_receipt_income_account(config):
    """
    Récupère le compte de produits utilisé pour les encaissements.
    """

    account_code = config.get(
        "receipt_income_account_code"
    )

    return get_active_account(
        account_code,
        "Produits - Encaissements",
    )


# ============================================================
# 7. COMPTE DE CHARGES
# ============================================================

def get_expense_account(expense, config):
    """
    Détermine le compte de charges selon la catégorie.
    """

    category_accounts = config.get(
        "expense_category_account_codes",
        {},
    )

    account_code = category_accounts.get(
        expense.category
    )

    if not account_code:
        account_code = config.get(
            "default_expense_account_code"
        )

    return get_active_account(
        account_code,
        f"Charges - {expense.category}",
    )


# ============================================================
# 8. CRÉATION DES LIGNES COMPTABLES
# ============================================================

def create_entry_lines(
    entry,
    debit_account,
    credit_account,
    amount,
    service,
    description,
):
    """
    Crée les deux lignes équilibrées d'une écriture comptable.
    """

    amount = Decimal(str(amount))

    if amount <= Decimal("0.00"):
        raise ValidationError(
            "Le montant de l'écriture doit être positif."
        )

    if debit_account.pk == credit_account.pk:
        raise ValidationError(
            "Le compte de débit et le compte de crédit "
            "ne peuvent pas être identiques."
        )

    EntryLine.objects.create(
        entry=entry,
        account=debit_account,
        service=service,
        description=description,
        debit=amount,
        credit=Decimal("0.00"),
    )

    EntryLine.objects.create(
        entry=entry,
        account=credit_account,
        service=service,
        description=description,
        debit=Decimal("0.00"),
        credit=amount,
    )


# ============================================================
# 9. VALIDATION ET COMPTABILISATION DE L'ÉCRITURE
# ============================================================

def finalize_accounting_entry(entry):
    """
    Vérifie l'équilibre de l'écriture et la comptabilise.
    """

    entry.validate_balance()

    entry.status = AccountingEntry.Status.POSTED

    entry.save(
        update_fields=["status"]
    )

    return entry


# ============================================================
# 10. CONTRÔLE DES DOUBLONS
# ============================================================

def get_existing_entry(operation_field, operation):
    """
    Vérifie si une opération possède déjà une écriture comptabilisée.
    """

    existing_entry = (
        AccountingEntry.objects
        .select_for_update()
        .filter(**{operation_field: operation})
        .first()
    )

    if not existing_entry:
        return None

    if existing_entry.status != AccountingEntry.Status.POSTED:
        raise ValidationError(
            "Une écriture existe déjà pour cette opération "
            "mais n'est pas comptabilisée. "
            "Une vérification manuelle est nécessaire."
        )

    return existing_entry


# ============================================================
# 11. COMPTABILISATION D'UN ENCAISSEMENT
# ============================================================

@transaction.atomic
def post_receipt(receipt, user):
    """
    Comptabilise automatiquement un encaissement.

    Débit  : compte de trésorerie
    Crédit : compte de produits
    """

    receipt = (
        Receipt.objects
        .select_for_update()
        .get(pk=receipt.pk)
    )

    if receipt.status != Receipt.Status.COMPLETED:
        raise ValidationError(
            "Seuls les encaissements terminés "
            "peuvent être comptabilisés."
        )

    if not receipt.validated:
        raise ValidationError(
            "L'encaissement doit être validé avant "
            "sa comptabilisation."
        )

    if not user or not user.is_authenticated:
        raise ValidationError(
            "Un utilisateur authentifié est requis."
        )

    existing_entry = get_existing_entry(
        "receipt",
        receipt,
    )

    if existing_entry:
        return existing_entry

    amount = validate_financial_operation(receipt)

    config = get_accounting_config()

    journal = get_journal_for_operation(
        receipt,
        config,
    )

    treasury_account = get_treasury_account(
        receipt,
        config,
    )

    income_account = get_receipt_income_account(
        config,
    )

    description = (
        f"Encaissement {receipt.reference} - "
        f"{receipt.description}"
    )

    entry = AccountingEntry.objects.create(
        date=receipt.date,
        journal=journal,
        description=description,
        status=AccountingEntry.Status.DRAFT,
        receipt=receipt,
        created_by=user,
    )

    create_entry_lines(
        entry=entry,
        debit_account=treasury_account,
        credit_account=income_account,
        amount=amount,
        service=receipt.service,
        description=description,
    )

    return finalize_accounting_entry(entry)


# ============================================================
# 12. COMPTABILISATION D'UN DÉCAISSEMENT
# ============================================================

@transaction.atomic
def post_cash_expense(expense, user):
    """
    Comptabilise automatiquement un décaissement.

    Débit  : compte de charges
    Crédit : compte de trésorerie
    """

    expense = (
        CashExpense.objects
        .select_for_update()
        .get(pk=expense.pk)
    )

    if expense.status != CashExpense.Status.COMPLETED:
        raise ValidationError(
            "Seuls les décaissements terminés "
            "peuvent être comptabilisés."
        )

    if not user or not user.is_authenticated:
        raise ValidationError(
            "Un utilisateur authentifié est requis."
        )

    existing_entry = get_existing_entry(
        "cash_expense",
        expense,
    )

    if existing_entry:
        return existing_entry

    amount = validate_financial_operation(expense)

    config = get_accounting_config()

    journal = get_journal_for_operation(
        expense,
        config,
    )

    treasury_account = get_treasury_account(
        expense,
        config,
    )

    expense_account = get_expense_account(
        expense,
        config,
    )

    description = (
        f"Décaissement {expense.reference} - "
        f"{expense.description}"
    )

    entry = AccountingEntry.objects.create(
        date=expense.date,
        journal=journal,
        description=description,
        status=AccountingEntry.Status.DRAFT,
        cash_expense=expense,
        created_by=user,
    )

    create_entry_lines(
        entry=entry,
        debit_account=expense_account,
        credit_account=treasury_account,
        amount=amount,
        service=expense.service,
        description=description,
    )

    return finalize_accounting_entry(entry)
