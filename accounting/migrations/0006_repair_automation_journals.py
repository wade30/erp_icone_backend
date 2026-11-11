from django.db import migrations


AUTOMATION_JOURNALS = {
    "BQ": "Banque",
    "CA": "Caisse",
    "MP": "Moyens de paiement",
    "OD": "Opérations diverses",
}


def repair_automation_journals(apps, schema_editor):
    Journal = apps.get_model("accounting", "Journal")
    manager = Journal.objects.using(schema_editor.connection.alias)

    for code, name in AUTOMATION_JOURNALS.items():
        manager.update_or_create(
            code=code,
            defaults={
                "name": name,
                "is_active": True,
            },
        )


class Migration(migrations.Migration):

    dependencies = [
        ("accounting", "0005_repair_automation_accounts"),
    ]

    operations = [
        migrations.RunPython(
            repair_automation_journals,
            migrations.RunPython.noop,
        ),
    ]
