from django.db import migrations


def allow_null_legacy_genre(apps, schema_editor):
    user_model = apps.get_model("users", "User")
    table_name = user_model._meta.db_table
    connection = schema_editor.connection

    with connection.cursor() as cursor:
        columns = connection.introspection.get_table_description(
            cursor, table_name
        )

    genre_column = next(
        (column for column in columns if column.name == "genre"),
        None,
    )
    if genre_column is None or genre_column.null_ok:
        return

    if connection.vendor != "postgresql":
        raise RuntimeError(
            "The legacy genre column migration requires PostgreSQL."
        )

    schema_editor.execute(
        f"ALTER TABLE {schema_editor.quote_name(table_name)} "
        f"ALTER COLUMN {schema_editor.quote_name('genre')} DROP NOT NULL"
    )


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0009_convert_user_id_to_bigint"),
    ]

    operations = [
        migrations.RunPython(
            allow_null_legacy_genre,
            migrations.RunPython.noop,
        ),
    ]
