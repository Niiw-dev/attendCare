from django.db import migrations


def fix_classifications(apps, schema_editor):
    ReconciliationDetail = apps.get_model('events', 'ReconciliationDetail')
    Attendance = apps.get_model('events', 'Attendance')

    details = ReconciliationDetail.objects.filter(classification='ASSIGNED')
    for detail in details:
        event = detail.reconciliation.event
        att = Attendance.objects.filter(
            server=detail.server,
            event=event,
        ).first()

        if att is not None and att.checkOutTime is None:
            detail.classification = 'INCOMPLETE'
            detail.save(update_fields=['classification'])

    incomplete_details = ReconciliationDetail.objects.filter(classification='VOLUNTEER')
    for detail in incomplete_details:
        event = detail.reconciliation.event
        att = Attendance.objects.filter(
            server=detail.server,
            event=event,
        ).first()

        if att is not None and att.checkOutTime is None:
            detail.classification = 'INCOMPLETE'
            detail.save(update_fields=['classification'])


def reverse_fix(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('events', '0016_add_incomplete_classification'),
    ]

    operations = [
        migrations.RunPython(fix_classifications, reverse_fix),
    ]
