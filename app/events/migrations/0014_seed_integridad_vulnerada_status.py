from django.db import migrations


def seed_integridad_vulnerada(apps, schema_editor):
    EventStatus = apps.get_model('events', 'EventStatus')
    EventStatus.objects.update_or_create(
        code='INTEGRIDAD_VULNERADA',
        defaults={'name': 'Integridad Vulnerada', 'color': '#dc2626', 'isActive': True}
    )


def reverse_integridad_vulnerada(apps, schema_editor):
    EventStatus = apps.get_model('events', 'EventStatus')
    EventStatus.objects.filter(code='INTEGRIDAD_VULNERADA').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('events', '0013_attendance_reconciliation_audit'),
    ]

    operations = [
        migrations.RunPython(seed_integridad_vulnerada, reverse_integridad_vulnerada),
    ]
