from django.db import migrations


def forwards(apps, schema_editor):
    LessonType = apps.get_model("timetable", "LessonType")
    LessonType.objects.filter(code="9").update(category="attestation")


def backwards(apps, schema_editor):
    LessonType = apps.get_model("timetable", "LessonType")
    LessonType.objects.filter(
        code="9", category="attestation",
    ).update(category="")


class Migration(migrations.Migration):

    dependencies = [
        ("timetable", "0010_discipline_workprogram"),   # ← подставь номер своей последней
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]