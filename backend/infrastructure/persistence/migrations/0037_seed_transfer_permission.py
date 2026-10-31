from django.db import migrations
def seed(apps,schema_editor):
 P=apps.get_model("persistence","SystemPermissionModel");P.objects.get_or_create(code="warehouse.transfer.post",defaults={"name":"Post stock transfers","description":"Post inter-warehouse transfers"})
class Migration(migrations.Migration):
 dependencies=[("persistence","0036_seed_stock_count_permission")]
 operations=[migrations.RunPython(seed,migrations.RunPython.noop)]
