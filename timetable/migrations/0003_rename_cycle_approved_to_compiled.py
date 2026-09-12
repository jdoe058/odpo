from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("timetable", "0002_lesson"),
    ]

    operations = [
        migrations.RenameField(
            model_name="cycle",
            old_name="approved_by",
            new_name="compiled_by",
        ),
    ]