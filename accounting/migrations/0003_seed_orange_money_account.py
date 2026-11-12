from django.db import migrations


def create_orange_money_account(apps, schema_editor):
    Account = apps.get_model("accounting", "Account")
    Account.objects.using(schema_editor.connection.alias).get_or_create(
        code="586",
        defaults={
            "name": "Trésorerie - Orange Money",
            "account_type": "ASSET",
            "is_active": True,
        },
    )


class Migration(migrations.Migration):

    dependencies = [
        ("accounting", "0002_alter_accountingentry_options_and_more"),
    ]

    operations = [
        migrations.RunPython(
            create_orange_money_account,
            migrations.RunPython.noop,
        ),
    ]
