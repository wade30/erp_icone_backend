from django.db import migrations


def create_wave_account(apps, schema_editor):
    Account = apps.get_model("accounting", "Account")
    Account.objects.using(schema_editor.connection.alias).get_or_create(
        code="585",
        defaults={
            "name": "Trésorerie - Wave",
            "account_type": "ASSET",
            "is_active": True,
        },
    )


class Migration(migrations.Migration):

    dependencies = [
        ("accounting", "0003_seed_orange_money_account"),
    ]

    operations = [
        migrations.RunPython(
            create_wave_account,
            migrations.RunPython.noop,
        ),
    ]
