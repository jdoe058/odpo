from django.db import migrations


def forwards(apps, schema_editor):
    Lesson = apps.get_model("timetable", "Lesson")
    for lesson in Lesson.objects.select_related("lesson_type").all():
        lesson.category = lesson.lesson_type.category or ""
        lesson.save(update_fields=["category"])


def backwards(apps, schema_editor):
    Lesson = apps.get_model("timetable", "Lesson")
    Lesson.objects.update(category="")


class Migration(migrations.Migration):

    dependencies = [
        ("timetable", "0016_lesson_category_lesson_group"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]