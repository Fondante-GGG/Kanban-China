from django.db import migrations
def seed(apps,schema_editor):
 P=apps.get_model("persistence","SystemPermissionModel");P.objects.get_or_create(code="warehouse.inventory.read",defaults={"name":"View warehouse inventory","description":"View stock balances and batches"})
class Migration(migrations.Migration):
 dependencies=[("persistence","0030_goods_certificates_prices")]
 operations=[migrations.RunPython(seed,migrations.RunPython.noop)]
