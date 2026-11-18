from django.db import migrations


def add_missing_role_column(apps, schema_editor):
    user_model = apps.get_model("users", "User")
    table_name = user_model._meta.db_table

    with schema_editor.connection.cursor() as cursor:
        columns = schema_editor.connection.introspection.get_table_description(
            cursor, table_name
        )

    if not any(column.name == "role" for column in columns):
        schema_editor.add_field(
            user_model, user_model._meta.get_field("role")
        )


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0005_alter_user_role"),
    ]

    operations = [
        migrations.RunPython(
            add_missing_role_column,
            migrations.RunPython.noop,
        ),
    ]
