from django.db import migrations, models


def convert_user_ids_to_bigint(apps, schema_editor):
    connection = schema_editor.connection
    if connection.vendor != "postgresql":
        raise RuntimeError("The user ID conversion requires PostgreSQL.")

    user_model = apps.get_model("users", "User")
    table_name = user_model._meta.db_table
    quote = connection.ops.quote_name

    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT namespace.nspname, relation.relname,
                   format_type(attribute.atttypid, attribute.atttypmod)
            FROM pg_class AS relation
            JOIN pg_namespace AS namespace
              ON namespace.oid = relation.relnamespace
            JOIN pg_attribute AS attribute
              ON attribute.attrelid = relation.oid
            WHERE relation.oid = to_regclass(%s)
              AND attribute.attname = 'id'
              AND NOT attribute.attisdropped
            """,
            [table_name],
        )
        table_info = cursor.fetchone()
        if table_info is None:
            raise RuntimeError(f"Could not find the {table_name}.id column.")

        schema_name, table_name, id_type = table_info
        qualified_table = f"{quote(schema_name)}.{quote(table_name)}"
        qualified_target = f"{quote(schema_name)}.{quote(table_name)}"

        cursor.execute(
            """
            SELECT namespace.nspname, relation.relname, constraint_row.conname,
                   pg_get_constraintdef(constraint_row.oid, true),
                   constraint_row.convalidated,
                   array_agg(attribute.attname ORDER BY key_column.ordinality)
            FROM pg_constraint AS constraint_row
            JOIN pg_class AS relation
              ON relation.oid = constraint_row.conrelid
            JOIN pg_namespace AS namespace
              ON namespace.oid = relation.relnamespace
            CROSS JOIN LATERAL
              unnest(constraint_row.conkey) WITH ORDINALITY
              AS key_column(attnum, ordinality)
            JOIN pg_attribute AS attribute
              ON attribute.attrelid = relation.oid
             AND attribute.attnum = key_column.attnum
            WHERE constraint_row.contype = 'f'
              AND constraint_row.confrelid = to_regclass(%s)
              AND constraint_row.confkey = ARRAY[
                    (
                        SELECT attnum
                        FROM pg_attribute
                        WHERE attrelid = constraint_row.confrelid
                          AND attname = 'id'
                          AND NOT attisdropped
                    )
                  ]::smallint[]
            GROUP BY namespace.nspname, relation.relname,
                     constraint_row.conname, constraint_row.oid,
                     constraint_row.convalidated
            ORDER BY namespace.nspname, relation.relname,
                     constraint_row.conname
            """,
            [qualified_target],
        )
        foreign_keys = cursor.fetchall()

        if id_type == "uuid":
            cursor.execute(
                f"""
                CREATE TEMP TABLE _users_user_id_map ON COMMIT DROP AS
                SELECT id AS old_id,
                       row_number() OVER (ORDER BY id)::bigint AS new_id
                FROM {qualified_table}
                """
            )
            cursor.execute(
                """
                ALTER TABLE pg_temp._users_user_id_map
                ADD PRIMARY KEY (old_id)
                """
            )
            cursor.execute(
                """
                CREATE UNIQUE INDEX _users_user_id_map_new_id_idx
                ON pg_temp._users_user_id_map (new_id)
                """
            )
            map_table = f"{quote('pg_temp')}.{quote('_users_user_id_map')}"
            map_function = (
                f"{quote('pg_temp')}.{quote('_users_user_uuid_to_bigint')}"
            )
            cursor.execute(
                f"""
                CREATE FUNCTION {map_function}(uuid)
                RETURNS bigint
                LANGUAGE SQL STABLE STRICT
                AS $function$
                    SELECT new_id
                    FROM {map_table}
                    WHERE old_id = $1
                $function$
                """
            )

            foreign_key_columns = sorted(
                {
                    (schema, table, column)
                    for schema, table, _, _, _, columns in foreign_keys
                    for column in columns
                }
            )

            for schema, table, column in foreign_key_columns:
                cursor.execute(
                    """
                    SELECT data_type
                    FROM information_schema.columns
                    WHERE table_schema = %s
                      AND table_name = %s
                      AND column_name = %s
                    """,
                    [schema, table, column],
                )
                column_type = cursor.fetchone()
                if column_type is None or column_type[0] != "uuid":
                    raise RuntimeError(
                        f"Unexpected type for {schema}.{table}.{column}; "
                        "expected uuid."
                    )

            for schema, table, constraint_name, _, _, _ in foreign_keys:
                cursor.execute(
                    f"ALTER TABLE {quote(schema)}.{quote(table)} "
                    f"DROP CONSTRAINT {quote(constraint_name)}"
                )

            for schema, table, column in foreign_key_columns:
                qualified_foreign_table = (
                    f"{quote(schema)}.{quote(table)}"
                )
                cursor.execute(
                    f"ALTER TABLE {qualified_foreign_table} "
                    f"ALTER COLUMN {quote(column)} TYPE bigint "
                    f"USING {map_function}({quote(column)})"
                )

            cursor.execute(
                f"ALTER TABLE {qualified_table} "
                f"ALTER COLUMN {quote('id')} DROP DEFAULT"
            )
            cursor.execute(
                f"ALTER TABLE {qualified_table} "
                f"ALTER COLUMN {quote('id')} TYPE bigint "
                f"USING {map_function}({quote('id')})"
            )

            for (
                schema,
                table,
                constraint_name,
                definition,
                validated,
                _,
            ) in foreign_keys:
                if not validated:
                    definition = f"{definition} NOT VALID"
                cursor.execute(
                    f"ALTER TABLE {quote(schema)}.{quote(table)} "
                    f"ADD CONSTRAINT {quote(constraint_name)} {definition}"
                )

            cursor.execute(f"DROP FUNCTION {map_function}(uuid)")
            cursor.execute(f"DROP TABLE {map_table}")
        elif id_type != "bigint":
            raise RuntimeError(
                f"Unexpected type for {table_name}.id: {id_type}."
            )

        if id_type == "bigint":
            for schema, table, _, _, _, columns in foreign_keys:
                for column in columns:
                    cursor.execute(
                        """
                        SELECT data_type
                        FROM information_schema.columns
                        WHERE table_schema = %s
                          AND table_name = %s
                          AND column_name = %s
                        """,
                        [schema, table, column],
                    )
                    column_type = cursor.fetchone()
                    if column_type is None or column_type[0] != "bigint":
                        raise RuntimeError(
                            f"Unexpected type for {schema}.{table}.{column}; "
                            "expected bigint."
                        )

        cursor.execute(
            "SELECT pg_get_serial_sequence(%s, 'id')",
            [qualified_target],
        )
        sequence_name = cursor.fetchone()[0]
        if sequence_name is None:
            sequence_name = f"{schema_name}.{table_name}_id_bigint_seq"
            cursor.execute("SELECT to_regclass(%s)", [sequence_name])
            if cursor.fetchone()[0] is not None:
                raise RuntimeError(
                    f"Sequence {sequence_name} already exists but is not "
                    "owned by the user ID column."
                )
            qualified_sequence = (
                f"{quote(schema_name)}.{quote(table_name + '_id_bigint_seq')}"
            )
            cursor.execute(
                f"CREATE SEQUENCE {qualified_sequence} AS bigint"
            )
            cursor.execute(
                f"ALTER SEQUENCE {qualified_sequence} "
                f"OWNED BY {qualified_table}.{quote('id')}"
            )

        cursor.execute(
            f"ALTER TABLE {qualified_table} "
            f"ALTER COLUMN {quote('id')} "
            "SET DEFAULT nextval(%s::regclass)",
            [sequence_name],
        )
        cursor.execute(
            f"SELECT COUNT(*), COALESCE(MAX({quote('id')}), 1) "
            f"FROM {qualified_table}"
        )
        row_count, max_id = cursor.fetchone()
        cursor.execute(
            "SELECT setval(%s::regclass, %s, %s)",
            [sequence_name, max_id, row_count > 0],
        )


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0008_preserve_user_uuid_primary_key"),
        ("accounting", "0007_alter_account_options_alter_accountingentry_options_and_more"),
        (
            "admin",
            "0001_initial",
        ),
        (
            "budgeting",
            "0002_alter_budget_options_alter_budgetline_options_and_more",
        ),
        ("communications", "0001_initial"),
        (
            "finance",
            "0006_cashexpense_budget_line_expenserequest_budget_line_and_more",
        ),
        ("incubator", "0001_initial"),
        ("orientation", "0001_initial"),
        (
            "preschool",
            "0003_attendance_justification_message_and_more",
        ),
    ]

    operations = [
        migrations.RunPython(convert_user_ids_to_bigint),
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.AlterField(
                    model_name="user",
                    name="id",
                    field=models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
            ],
        ),
    ]
