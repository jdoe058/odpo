from datetime import date, time

from django.test import TestCase

from timetable.models import (
    Base, Cycle, CycleName, Employee, FundingType, Lesson, LessonType, Position,
)
from timetable.services.grid import calculate_grid


class GridTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.pos = Position.objects.create(
            name="преподаватель", max_hours_per_day=6, sort_order=50,
        )
        cls.emp = Employee.objects.create(
            short_name="ИВАНОВ И.И.", position=cls.pos,
        )
        cls.lt = LessonType.objects.create(
            code="0", name="лекция", sort_order=10, counts_in_hours=True,
        )
        cls.lt_exam = LessonType.objects.create(
            code="9", name="итоговая аттестация",
            sort_order=30, counts_in_hours=False,
        )
        cls.funding = FundingType.objects.create(name="БЮДЖЕТ")
        cls.base = Base.objects.create(name="КОРПУС")
        cls.cname = CycleName.objects.create(name="ЦИКЛ")
        cls.cycle = Cycle.objects.create(
            name=cls.cname, funding_type=cls.funding, base=cls.base,
            start_date=date(2026, 9, 7), end_date=date(2026, 9, 13),
            compiled_by=cls.emp,
        )

    def _lesson(self, d, hours, lt=None):
        return Lesson.objects.create(
            cycle=self.cycle, date=d, time_start=time(9, 0),
            hours=hours, lesson_type=lt or self.lt, employee=self.emp,
        )

    def test_only_counting_types_in_total(self):
        self._lesson(date(2026, 9, 7), 4)
        self._lesson(date(2026, 9, 7), 100, lt=self.lt_exam)
        grid = calculate_grid(date(2026, 9, 7), date(2026, 9, 13))
        self.assertEqual(grid.rows[0].total, 4)

    def test_over_limit_marks_cell(self):
        self._lesson(date(2026, 9, 7), 8)
        grid = calculate_grid(date(2026, 9, 7), date(2026, 9, 7))
        self.assertTrue(grid.rows[0].cells[0].over_limit)

    def test_cells_within_limits_not_marked(self):
        self._lesson(date(2026, 9, 7), 6)
        grid = calculate_grid(date(2026, 9, 7), date(2026, 9, 7))
        self.assertFalse(grid.rows[0].cells[0].over_limit)
