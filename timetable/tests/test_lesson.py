"""
Тесты модели Lesson: база и перемена.

Проверяют:
* effective_base: своя база, фолбэк на базу цикла;
* available_from: окончание + перемена;
* break_after_minutes по умолчанию 10;
* time_end не меняется при ненулевой перемене.
"""
from datetime import date, time

from django.test import TestCase

from timetable.models import Cycle, Lesson, LessonType
from timetable.tests._factories import (
    make_base, make_cycle, make_cycle_name, make_employee,
    make_funding_type, make_position,
)


class LessonBaseAndBreakTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        pos = make_position("преподаватель")
        cls.emp = make_employee("ИВАНОВ И.И.", pos)
        cls.base_main = make_base("КОРПУС №1")
        cls.base_other = make_base("ВЫЕЗДНОЙ КЛАСС")
        funding = make_funding_type("БЮДЖЕТ")
        cname = make_cycle_name("ЦИКЛ")
        cls.cycle = make_cycle(
            name=cname, base=cls.base_main, funding=funding,
            compiled_by=cls.emp,
            start_date=date(2026, 9, 1), end_date=date(2026, 9, 30),
        )
        cls.lt = LessonType.objects.create(
            code="0", name="лекция", sort_order=10, counts_in_hours=True,
        )

    def _lesson(self, *, base=None, break_minutes=None, hours=2,
                time_start=time(9, 0)):
        kwargs = {"hours": hours, "time_start": time_start}
        if base is not None:
            kwargs["base"] = base
        if break_minutes is not None:
            kwargs["break_after_minutes"] = break_minutes
        return Lesson.objects.create(
            cycle=self.cycle, date=date(2026, 9, 1),
            lesson_type=self.lt, employee=self.emp, **kwargs,
        )


class EffectiveBaseTests(LessonBaseAndBreakTests):

    def test_falls_back_to_cycle_base(self):
        lesson = self._lesson()  # base не задан
        self.assertIsNone(lesson.base)
        self.assertEqual(lesson.effective_base, self.base_main)

    def test_returns_own_base(self):
        lesson = self._lesson(base=self.base_other)
        self.assertEqual(lesson.effective_base, self.base_other)
        # База цикла при этом не меняется.
        self.assertEqual(lesson.cycle.base, self.base_main)


class BreakAfterTests(LessonBaseAndBreakTests):

    def test_default_break_is_10(self):
        lesson = self._lesson()
        self.assertEqual(lesson.break_after_minutes, 10)

    def test_explicit_break_zero(self):
        lesson = self._lesson(break_minutes=0)
        self.assertEqual(lesson.break_after_minutes, 0)

    def test_explicit_break(self):
        lesson = self._lesson(break_minutes=30)
        self.assertEqual(lesson.break_after_minutes, 30)


class AvailableFromTests(LessonBaseAndBreakTests):

    def test_available_from_adds_break(self):
        # 09:00 + 2 × 45 мин = 10:30; + 10 мин = 10:40.
        lesson = self._lesson(hours=2, break_minutes=10)
        self.assertEqual(lesson.time_end, time(10, 30))
        self.assertEqual(lesson.available_from, time(10, 40))

    def test_available_from_zero_break(self):
        lesson = self._lesson(hours=2, break_minutes=0)
        self.assertEqual(lesson.available_from, time(10, 30))

    def test_available_from_long_break(self):
        # 09:00 + 90 мин = 10:30; + 40 мин = 11:10.
        lesson = self._lesson(hours=2, break_minutes=40)
        self.assertEqual(lesson.available_from, time(11, 10))

    def test_time_end_unchanged_by_break(self):
        """Перемена не влияет на time_end — это свойство урока."""
        lesson = self._lesson(hours=2, break_minutes=40)
        self.assertEqual(lesson.time_end, time(10, 30))