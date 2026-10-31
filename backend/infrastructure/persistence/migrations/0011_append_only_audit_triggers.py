from django.db import migrations


TABLES = ("document_versions", "operation_logs", "approval_actions")


def install_append_only_triggers(apps, schema_editor):
    """Enforce audit immutability below the ORM for PostgreSQL deployments.

    SQLite is used by local/unit tests and does not support PL/pgSQL.  The
    model manager remains the portable guard there; production PostgreSQL has
    this additional database boundary.
    """
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute("""
        CREATE OR REPLACE FUNCTION yrys_prevent_audit_mutation()
        RETURNS trigger AS $$
        BEGIN
          RAISE EXCEPTION 'append-only audit record';
        END;
        $$ LANGUAGE plpgsql;
    """)
    for table in TABLES:
        schema_editor.execute(
            f"CREATE TRIGGER {table}_append_only "
            f"BEFORE UPDATE OR DELETE ON {table} "
            "FOR EACH ROW EXECUTE FUNCTION yrys_prevent_audit_mutation();"
        )


def remove_append_only_triggers(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    for table in TABLES:
        schema_editor.execute(f"DROP TRIGGER IF EXISTS {table}_append_only ON {table};")
    schema_editor.execute("DROP FUNCTION IF EXISTS yrys_prevent_audit_mutation();")


class Migration(migrations.Migration):
    dependencies = [("persistence", "0010_approval_flow_request_links")]

    operations = [migrations.RunPython(install_append_only_triggers, remove_append_only_triggers)]
