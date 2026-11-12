from django.db import migrations


AUTOMATION_ACCOUNTS = {
    "571": ("Trésorerie - Caisse", "ASSET"),
    "585": ("Trésorerie - Wave", "ASSET"),
    "586": ("Trésorerie - Orange Money", "ASSET"),
    "588": ("Trésorerie - Autres paiements", "ASSET"),
    "521": ("Banque 1", "ASSET"),
    "522": ("Banque 2", "ASSET"),
    "706": ("Produits - Encaissements", "INCOME"),
    "625": ("Charges - Dépenses", "EXPENSE"),
    "624": ("Charges - Transport", "EXPENSE"),
    "626": ("Charges - Communication", "EXPENSE"),
    "605": ("Charges - Fournitures", "EXPENSE"),
}


def repair_automation_accounts(apps, schema_editor):
    Account = apps.get_model("accounting", "Account")
    manager = Account.objects.using(schema_editor.connection.alias)

    for code, (name, account_type) in AUTOMATION_ACCOUNTS.items():
        manager.update_or_create(
            code=code,
            defaults={
                "name": name,
                "account_type": account_type,
                "is_active": True,
            },
        )


class Migration(migrations.Migration):

    dependencies = [
        ("accounting", "0004_seed_wave_account"),
    ]

    operations = [
        migrations.RunPython(
            repair_automation_accounts,
            migrations.RunPython.noop,
        ),
    ]
