from django.db import migrations
def seed(apps,schema_editor):
 P=apps.get_model("persistence","SystemPermissionModel");P.objects.get_or_create(code="warehouse.count.approve",defaults={"name":"Approve stock counts","description":"Approve inventory adjustments"})
class Migration(migrations.Migration):
 dependencies=[("persistence","0035_admin_licenses")]
 operations=[migrations.RunPython(seed,migrations.RunPython.noop)]
