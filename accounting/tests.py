from django.test import TestCase

from .models import Account
from .services import get_active_account, get_active_journal


class OrangeMoneyAccountTests(TestCase):
    def test_default_orange_money_treasury_account_is_available(self):
        account = get_active_account(
            "586",
            "Trésorerie - ORANGE_MONEY",
        )

        self.assertEqual(account.name, "Trésorerie - Orange Money")
        self.assertEqual(account.account_type, Account.AccountType.ASSET)

    def test_default_wave_treasury_account_is_available(self):
        account = get_active_account(
            "585",
            "Trésorerie - WAVE",
        )

        self.assertEqual(account.name, "Trésorerie - Wave")
        self.assertEqual(account.account_type, Account.AccountType.ASSET)

    def test_all_automation_accounts_exist_and_are_active(self):
        expected_accounts = {
            "571": Account.AccountType.ASSET,
            "585": Account.AccountType.ASSET,
            "586": Account.AccountType.ASSET,
            "588": Account.AccountType.ASSET,
            "521": Account.AccountType.ASSET,
            "522": Account.AccountType.ASSET,
            "706": Account.AccountType.INCOME,
            "625": Account.AccountType.EXPENSE,
            "624": Account.AccountType.EXPENSE,
            "626": Account.AccountType.EXPENSE,
            "605": Account.AccountType.EXPENSE,
        }

        for code, account_type in expected_accounts.items():
            with self.subTest(code=code):
                account = get_active_account(code, "Compte automatique")
                self.assertEqual(account.account_type, account_type)

    def test_all_automation_journals_exist_and_are_active(self):
        expected_journals = {
            "BQ": "Banque",
            "CA": "Caisse",
            "MP": "Moyens de paiement",
            "OD": "Opérations diverses",
        }

        for code, name in expected_journals.items():
            with self.subTest(code=code):
                journal = get_active_journal(code)
                self.assertEqual(journal.name, name)
