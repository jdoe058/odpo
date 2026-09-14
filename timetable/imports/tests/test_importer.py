from datetime import date
from django.test import TestCase

from timetable.models import (
    Base, Cycle, CycleName, Employee, FundingType,
    Lesson, LessonType, Position,
)
from timetable.imports import (
    ScheduleImportError, import_schedule,
)
from timetable.imports.importer import parse_header, write_cycle, Header, ParsedLesson
from timetable.imports.tests.fixtures import make_xlsx


def default_header() -> dict:
    return {
        "A1": "ИВАНОВ И.И.",
        "A2": "БЮДЖЕТ",
        "A3": "ОСНОВНАЯ БАЗА",
        "A4": "ОХРАНА ТРУДА",
        "A5": "01.09.2026",
        "A6": "30.09.2026",
    }


class ImporterFixtureMixin:
    @classmethod
    def setUpTestData(cls):
        cls.position = Position.objects.create(name="Преподаватель", max_hours_per_day=6)
        cls.teacher = Employee.objects.create(short_name="ИВАНОВ И.И.", position=cls.position)
        cls.funding = FundingType.objects.create(name="БЮДЖЕТ")
        cls.base = Base.objects.create(name="ОСНОВНАЯ БАЗА")
        cls.cycle_name = CycleName.objects.create(name="ОХРАНА ТРУДА")
        cls.lesson_type = LessonType.objects.create(
            code="LEC", name="Лекция", sort_order=10,
            counts_in_hours=True, category="lecture",
        )


class ImportScheduleHappyPathTests(ImporterFixtureMixin, TestCase):
    def test_creates_cycle_and_lessons(self):
        xlsx = make_xlsx(default_header(), [
            ("01.09.2026", "09:00-10:30", 2, "LEC", "Тема 1", "ИВАНОВ И.И."),
            ("02.09.2026", "09:00-10:30", 2, "LEC", "Тема 2", "ИВАНОВ И.И."),
        ])

        result = import_schedule(xlsx)

        self.assertEqual(result.lessons_created, 2)
        self.assertEqual(result.cycle.lessons.count(), 2)
        self.assertEqual(result.cycle.name, self.cycle_name)

    def test_reimport_replaces_lessons(self):
        xlsx = make_xlsx(default_header(), [
            ("01.09.2026", "09:00-10:30", 2, "LEC", "Старое", "ИВАНОВ И.И."),
        ])
        import_schedule(xlsx)

        xlsx = make_xlsx(default_header(), [
            ("03.09.2026", "09:00-10:30", 2, "LEC", "Новое", "ИВАНОВ И.И."),
        ])
        import_schedule(xlsx)

        lessons = Lesson.objects.all()
        self.assertEqual(lessons.count(), 1)
        self.assertEqual(lessons.first().topic, "Новое")


class ImportScheduleAtomicityTests(ImporterFixtureMixin, TestCase):
    def test_no_writes_when_errors(self):
        xlsx = make_xlsx(default_header(), [
            ("01.09.2026", "09:00-10:30", 2, "LEC", "Ок", "ИВАНОВ И.И."),
            ("плохая дата", "09:00-10:30", 2, "LEC", "Плохо", "ИВАНОВ И.И."),
        ])

        with self.assertRaises(ScheduleImportError):
            import_schedule(xlsx)

        self.assertEqual(Cycle.objects.count(), 0)
        self.assertEqual(Lesson.objects.count(), 0)

    def test_unknown_teacher_reported(self):
        xlsx = make_xlsx(default_header(), [
            ("01.09.2026", "09:00-10:30", 2, "LEC", "X", "ПЕТРОВ П.П."),
        ])

        with self.assertRaises(ScheduleImportError) as cm:
            import_schedule(xlsx)

        self.assertTrue(any("ПЕТРОВ" in e for e in cm.exception.errors))
        self.assertEqual(Lesson.objects.count(), 0)

    def test_unknown_lesson_type_reported(self):
        xlsx = make_xlsx(default_header(), [
            ("01.09.2026", "09:00-10:30", 2, "XXX", "X", "ИВАНОВ И.И."),
        ])

        with self.assertRaises(ScheduleImportError) as cm:
            import_schedule(xlsx)

        self.assertTrue(any("XXX" in e for e in cm.exception.errors))


class WriteCycleTests(ImporterFixtureMixin, TestCase):
    """Тест фазы 4 в изоляции — без XLSX."""

    def test_creates_cycle(self):
        header = Header(
            cycle_name=self.cycle_name,
            funding=self.funding,
            base=self.base,
            compiled_by=self.teacher,
            start_date=date(2026, 9, 1),
            end_date=date(2026, 9, 30),
        )
        lessons = [
            ParsedLesson(
                row_idx=7, date=date(2026, 9, 1),
                time_start=__import__("datetime").time(9),
                time_end=__import__("datetime").time(10, 30),
                hours=2, lesson_type=self.lesson_type,
                topic="Тема", employee=self.teacher,
            ),
        ]

        result = write_cycle(header, lessons)

        self.assertEqual(result.lessons_created, 1)
        self.assertEqual(result.cycle.lessons.count(), 1)

