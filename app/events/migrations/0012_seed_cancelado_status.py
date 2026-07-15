from django.db import migrations


def seed_cancelado(apps, schema_editor):
    EventStatus = apps.get_model('events', 'EventStatus')
    EventStatus.objects.update_or_create(
        code='CANCELADO',
        defaults={'name': 'Cancelado', 'color': '#f59e0b', 'isActive': True}
    )


def reverse_cancelado(apps, schema_editor):
    EventStatus = apps.get_model('events', 'EventStatus')
    EventStatus.objects.filter(code='CANCELADO').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('events', '0011_assignment'),
    ]

    operations = [
        migrations.RunPython(seed_cancelado, reverse_cancelado),
    ]
