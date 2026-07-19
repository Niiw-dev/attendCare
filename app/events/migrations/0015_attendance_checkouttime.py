# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('events', '0014_seed_integridad_vulnerada_status'),
    ]

    operations = [
        migrations.AddField(
            model_name='attendance',
            name='checkOutTime',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
