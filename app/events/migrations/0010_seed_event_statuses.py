from django.db import migrations


def seed_statuses(apps, schema_editor):
    EventStatus = apps.get_model('events', 'EventStatus')
    statuses = [
        {'code': 'PROGRAMADO', 'name': 'Programado', 'color': '#6b7280'},
        {'code': 'ACTIVO', 'name': 'Activo', 'color': '#22c55e'},
        {'code': 'FINALIZADO', 'name': 'Finalizado', 'color': '#ef4444'},
        {'code': 'RECONCILIADO', 'name': 'Reconciliado', 'color': '#3b82f6'},
    ]
    for s in statuses:
        EventStatus.objects.update_or_create(
            code=s['code'],
            defaults={'name': s['name'], 'color': s['color'], 'isActive': True}
        )


def reverse_statuses(apps, schema_editor):
    EventStatus = apps.get_model('events', 'EventStatus')
    EventStatus.objects.filter(code__in=[
        'PROGRAMADO', 'ACTIVO', 'FINALIZADO', 'RECONCILIADO'
    ]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('events', '0009_add_eventstatus_code'),
    ]

    operations = [
        migrations.RunPython(seed_statuses, reverse_statuses),
    ]
