from datetime import date

from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from accounting.models import Account, AccountingEntry, Journal
from users.models import User
from .models import BankAccount, CashExpense, ExpenseRequest, Receipt


@override_settings(
    ACCOUNTING_AUTOMATION={
        "receipt_journal_codes": {
            Receipt.PaymentMethod.CASH: "CA",
        },
        "expense_journal_codes": {
            Receipt.PaymentMethod.CASH: "CA",
        },
        "receipt_income_account_code": "706",
        "default_expense_account_code": "625",
        "payment_account_codes": {
            Receipt.PaymentMethod.CASH: "571",
        },
    }
)
class FinanceOperationCreationTests(TestCase):
    def setUp(self):
        self.finance_user = User.objects.create_user(
            username="finance",
            role=User.Role.FINANCE,
            service=User.Service.GENERAL,
        )
        self.client = APIClient()
        self.client.force_authenticate(self.finance_user)

        Journal.objects.get_or_create(
            code="CA",
            defaults={"name": "Caisse"},
        )
        Account.objects.get_or_create(
            code="571",
            defaults={
                "name": "Caisse",
                "account_type": Account.AccountType.ASSET,
            },
        )
        Account.objects.get_or_create(
            code="706",
            defaults={
                "name": "Produits",
                "account_type": Account.AccountType.INCOME,
            },
        )
        Account.objects.get_or_create(
            code="625",
            defaults={
                "name": "Charges",
                "account_type": Account.AccountType.EXPENSE,
            },
        )

    def test_finance_created_receipt_is_completed_and_posted(self):
        response = self.client.post(
            "/api/finance/receipts/",
            {
                "date": "2026-11-02",
                "description": "Paiement en espèces",
                "service": User.Service.INSTITUTE,
                "amount": "25000",
                "payment_method": Receipt.PaymentMethod.CASH,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            response.data["status"],
            Receipt.Status.COMPLETED,
        )
        receipt = Receipt.objects.get()
        self.assertTrue(receipt.validated)
        self.assertEqual(
            receipt.accounting_entry.status,
            AccountingEntry.Status.POSTED,
        )

    def test_finance_created_cash_expense_is_completed_and_posted(self):
        response = self.client.post(
            "/api/finance/cash-expenses/",
            {
                "date": "2026-11-02",
                "service": User.Service.INSTITUTE,
                "category": "Fournitures",
                "description": "Achat de papier",
                "amount": "2500",
                "payment_method": Receipt.PaymentMethod.CASH,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            response.data["status"],
            CashExpense.Status.COMPLETED,
        )
        expense = CashExpense.objects.get()
        self.assertEqual(
            expense.accounting_entry.status,
            AccountingEntry.Status.POSTED,
        )

    def test_finance_can_generate_receipt_references_before_completion(self):
        response = self.client.post(
            "/api/finance/receipts/",
            {"service": User.Service.INSTITUTE},
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["status"], Receipt.Status.DRAFT)
        self.assertTrue(response.data["reference"])
        self.assertTrue(response.data["payment_reference"])
        self.assertFalse(AccountingEntry.objects.exists())

    def test_finance_can_generate_expense_references_before_completion(self):
        response = self.client.post(
            "/api/finance/cash-expenses/",
            {"service": User.Service.INSTITUTE},
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["status"], CashExpense.Status.DRAFT)
        self.assertTrue(response.data["reference"])
        self.assertTrue(response.data["payment_reference"])
        self.assertFalse(AccountingEntry.objects.exists())

    @override_settings(
        ACCOUNTING_AUTOMATION={
            "receipt_journal_codes": {
                Receipt.PaymentMethod.CASH: "MISSING",
            },
        }
    )
    def test_failed_accounting_rolls_back_finance_receipt_creation(self):
        response = self.client.post(
            "/api/finance/receipts/",
            {
                "date": "2026-11-02",
                "description": "Paiement en espèces",
                "service": User.Service.INSTITUTE,
                "amount": "25000",
                "payment_method": Receipt.PaymentMethod.CASH,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(Receipt.objects.exists())
        self.assertFalse(AccountingEntry.objects.exists())

    def test_paying_expense_requires_a_payment_method(self):
        expense_request = ExpenseRequest.objects.create(
            date=date(2026, 11, 2),
            service=User.Service.INSTITUTE,
            category="Fournitures",
            description="Achat de papier",
            amount="2500",
            requested_by=self.finance_user,
            status=ExpenseRequest.Status.APPROVED,
        )

        response = self.client.post(
            f"/api/finance/expenses/{expense_request.pk}/pay/",
            {},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            str(response.data["payment_method"]),
            "Le mode de paiement est obligatoire.",
        )
        self.assertFalse(CashExpense.objects.exists())

    def test_active_bank_account_list_excludes_inactive_accounts(self):
        active_account = BankAccount.objects.create(
            name="Compte actif",
            bank_name="Banque",
            is_active=True,
        )
        inactive_account = BankAccount.objects.create(
            name="Compte inactif",
            bank_name="Banque",
            is_active=False,
        )

        response = self.client.get(
            "/api/finance/bank-accounts/?is_active=true"
        )

        self.assertEqual(response.status_code, 200)
        returned_ids = {
            account["id"]
            for account in response.data["results"]
        }
        self.assertIn(active_account.id, returned_ids)
        self.assertNotIn(inactive_account.id, returned_ids)


@override_settings(
    ACCOUNTING_AUTOMATION={
        "receipt_journal_codes": {
            Receipt.PaymentMethod.WAVE: "MISSING",
        },
    }
)
class ReceiptCompletionAccountingErrorTests(TestCase):
    def setUp(self):
        self.finance_user = User.objects.create_user(
            username="finance",
            role=User.Role.FINANCE,
            service=User.Service.GENERAL,
        )
        self.client = APIClient()
        self.client.force_authenticate(self.finance_user)
        self.receipt = Receipt.objects.create(
            date=date(2026, 11, 2),
            description="Paiement Wave",
            service=User.Service.INSTITUTE,
            amount="25000",
            payment_method=Receipt.PaymentMethod.WAVE,
            created_by=self.finance_user,
        )

    def test_missing_journal_returns_validation_error_and_rolls_back(self):
        response = self.client.post(
            f"/api/finance/receipts/{self.receipt.pk}/complete/",
            {},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.data["detail"],
            ["Le journal MISSING n'existe pas ou est inactif."],
        )

        self.receipt.refresh_from_db()
        self.assertEqual(self.receipt.status, Receipt.Status.DRAFT)
        self.assertFalse(self.receipt.validated)
        self.assertFalse(AccountingEntry.objects.exists())


class ExpenseRequestSubmissionTests(TestCase):
    def setUp(self):
        self.manager = User.objects.create_user(
            username="manager",
            password="test-password",
            role=User.Role.SERVICE_MANAGER,
            service=User.Service.INSTITUTE,
        )
        self.client = APIClient()
        self.client.force_authenticate(self.manager)

    def make_expense(self, service=User.Service.INSTITUTE, status=ExpenseRequest.Status.DRAFT):
        return ExpenseRequest.objects.create(
            reference=f"EXP-{ExpenseRequest.objects.count() + 1}",
            date="2026-11-02",
            service=service,
            category="Fournitures",
            description="Achat de fournitures",
            amount=2500,
            requested_by=self.manager,
            status=status,
        )

    def test_manager_can_record_paid_expense_for_their_service(self):
        response = self.client.post(
            "/api/finance/cash-expenses/",
            {
                "reference": "CASH-1",
                "date": "2026-11-02",
                "service": User.Service.INSTITUTE,
                "category": "Fournitures",
                "description": "Achat de papier",
                "supplier": "Papeterie",
                "amount": "2500",
                "payment_method": "CASH",
                "payment_reference": "REC-123",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["recorded_by"], str(self.manager))
        self.assertEqual(
            CashExpense.objects.get(reference="CASH-1").service,
            User.Service.INSTITUTE,
        )

    def test_manager_cannot_record_cash_expense_for_another_service(self):
        response = self.client.post(
            "/api/finance/cash-expenses/",
            {
                "reference": "CASH-2",
                "date": "2026-11-02",
                "service": User.Service.MARKETING,
                "category": "Fournitures",
                "description": "Achat de papier",
                "amount": "2500",
                "payment_method": "CASH",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 403)
        self.assertFalse(CashExpense.objects.exists())

    def test_finance_user_can_record_expense_for_another_service(self):
        finance_user = User.objects.create_user(
            username="finance",
            password="test-password",
            role=User.Role.FINANCE,
            service=User.Service.INSTITUTE,
        )
        self.client.force_authenticate(finance_user)

        response = self.client.post(
            "/api/finance/cash-expenses/",
            {
                "reference": "CASH-FINANCE-1",
                "date": "2026-11-02",
                "service": User.Service.MARKETING,
                "category": "Fournitures",
                "description": "Achat de papier",
                "amount": "2500",
                "payment_method": "CASH",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            CashExpense.objects.get(reference="CASH-FINANCE-1").service,
            User.Service.MARKETING,
        )

    def test_cash_expense_is_not_editable_after_recording(self):
        expense = CashExpense.objects.create(
            reference="CASH-3",
            date="2026-11-02",
            service=User.Service.INSTITUTE,
            category="Fournitures",
            description="Achat de papier",
            amount=2500,
            payment_method=Receipt.PaymentMethod.CASH,
            recorded_by=self.manager,
        )

        response = self.client.patch(
            f"/api/finance/cash-expenses/{expense.pk}/",
            {"amount": "5000"},
            format="json",
        )

        self.assertEqual(response.status_code, 403)
        expense.refresh_from_db()
        self.assertEqual(expense.amount, 2500)

    def test_manager_can_create_receipt_for_their_service(self):
        response = self.client.post(
            "/api/finance/receipts/",
            {
                "reference": "REC-1",
                "date": "2026-11-02",
                "description": "Paiement d'une inscription",
                "service": User.Service.INSTITUTE,
                "amount": "25000",
                "payment_method": "CASH",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["service"], User.Service.INSTITUTE)

    def test_manager_can_create_expense_request_for_their_service(self):
        response = self.client.post(
            "/api/finance/expenses/",
            {
                "reference": "EXP-1",
                "date": "2026-11-02",
                "service": User.Service.INSTITUTE,
                "category": "Fournitures",
                "description": "Achat de fournitures",
                "amount": "2500",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["status"], ExpenseRequest.Status.DRAFT)

    def test_manager_cannot_edit_submitted_expense(self):
        expense = self.make_expense(status=ExpenseRequest.Status.SUBMITTED)

        response = self.client.patch(
            f"/api/finance/expenses/{expense.pk}/",
            {"amount": "5000"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)

    def test_manager_cannot_edit_validated_receipt(self):
        receipt = Receipt.objects.create(
            reference="REC-VALID",
            date="2026-11-02",
            description="Encaissement validé",
            service=User.Service.INSTITUTE,
            amount=25000,
            payment_method=Receipt.PaymentMethod.CASH,
            created_by=self.manager,
            validated=True,
        )

        response = self.client.patch(
            f"/api/finance/receipts/{receipt.pk}/",
            {"description": "Modification"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)

    def test_manager_can_submit_draft_for_their_service(self):
        expense = self.make_expense()

        response = self.client.post(
            f"/api/finance/expenses/{expense.pk}/submit/",
            {},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        expense.refresh_from_db()
        self.assertEqual(expense.status, ExpenseRequest.Status.SUBMITTED)

    def test_manager_cannot_submit_expense_from_another_service(self):
        expense = self.make_expense(service=User.Service.MARKETING)

        response = self.client.post(
            f"/api/finance/expenses/{expense.pk}/submit/",
            {},
            format="json",
        )

        self.assertEqual(response.status_code, 404)

    def test_submitted_expense_cannot_be_submitted_again(self):
        expense = self.make_expense(status=ExpenseRequest.Status.SUBMITTED)

        response = self.client.post(
            f"/api/finance/expenses/{expense.pk}/submit/",
            {},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
