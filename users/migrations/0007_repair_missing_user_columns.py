from django.db import migrations


def add_missing_user_columns(apps, schema_editor):
    user_model = apps.get_model("users", "User")
    table_name = user_model._meta.db_table

    with schema_editor.connection.cursor() as cursor:
        columns = schema_editor.connection.introspection.get_table_description(
            cursor, table_name
        )

    existing_columns = {column.name for column in columns}

    for field_name in ("service", "telephone", "fonction"):
        field = user_model._meta.get_field(field_name)
        if field.column not in existing_columns:
            schema_editor.add_field(user_model, field)
            existing_columns.add(field.column)


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0006_repair_missing_user_role_column"),
    ]

    operations = [
        migrations.RunPython(
            add_missing_user_columns,
            migrations.RunPython.noop,
        ),
    ]
