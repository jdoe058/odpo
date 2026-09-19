from datetime import date, time

from django.test import TestCase

from timetable.models import (
    Base, Cycle, CycleName, Employee, FundingType, Lesson, LessonType,
    Position,
)
from timetable.services.limits import (
    SCOPES, calculate_overtime
)


class LimitsBase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.pos_teacher = Position.objects.create(
            name="преподаватель",
            max_hours_per_day=6,
            max_hours_per_week=36,
            max_hours_per_year=720,
            sort_order=50,
        )
        cls.pos_chief = Position.objects.create(
            name="директор", max_hours_per_day=0, sort_order=10,
        )
        cls.pos_year = Position.objects.create(
            name="тест-год",
            max_hours_per_day=10,
            max_hours_per_week=100,
            max_hours_per_year=10,
            sort_order=99,
        )
        cls.teacher = Employee.objects.create(
            short_name="ИВАНОВ И.И.", position=cls.pos_teacher,
        )
        cls.chief = Employee.objects.create(
            short_name="ПЕТРОВ П.П.", position=cls.pos_chief,
        )
        cls.year_emp = Employee.objects.create(
            short_name="СИДОРОВ С.С.", position=cls.pos_year,
        )
        cls.lt_lecture = LessonType.objects.create(
            code="0", name="лекция", sort_order=10, counts_in_hours=True,
        )
        cls.lt_exam = LessonType.objects.create(
            code="9", name="итоговая аттестация",
            sort_order=30, counts_in_hours=False,
        )

        cls.funding = FundingType.objects.create(name="БЮДЖЕТ")
        cls.base = Base.objects.create(name="КОРПУС №1")
        cls.cname = CycleName.objects.create(name="ОХРАНА ТРУДА")
        cls.cycle = Cycle.objects.create(
            name=cls.cname, funding_type=cls.funding, base=cls.base,
            start_date=date(2026, 9, 1), end_date=date(2026, 9, 30),
            compiled_by=cls.teacher,
        )

    def _db_lesson(self, *, d, hours, employee=None, lt=None):
        return Lesson.objects.create(
            cycle=self.cycle,
            date=d, time_start=time(9, 0), hours=hours,
            lesson_type=lt or self.lt_lecture,
            employee=employee or self.teacher,
        )


class CalculateOvertimeTests(LimitsBase):
    def test_no_overtime_returns_empty(self):
        self._db_lesson(d=date(2026, 9, 1), hours=4)
        for scope in SCOPES:
            self.assertEqual(calculate_overtime(scope), ())

    def test_day_overtime(self):
        self._db_lesson(d=date(2026, 9, 1), hours=8)
        result = calculate_overtime("day")
        self.assertEqual(len(result), 1)
        o = result[0]
        self.assertEqual(o.employee, self.teacher)
        self.assertEqual(o.scope, "day")
        self.assertEqual(o.total_excess, 2)
        self.assertEqual(o.limit, 6)
        self.assertEqual(o.items[0].period_start, date(2026, 9, 1))

    def test_week_overtime(self):
        for i in range(7):
            self._db_lesson(d=date(2026, 9, 7 + i), hours=6)
        result = calculate_overtime("week")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].total_excess, 6)  # 42 - 36
        self.assertEqual(result[0].items[0].period_start, date(2026, 9, 7))

    def test_year_overtime(self):
        self._db_lesson(d=date(2026, 9, 1), hours=8, employee=self.year_emp)
        self._db_lesson(d=date(2026, 10, 1), hours=8, employee=self.year_emp)
        result = calculate_overtime("year")
        matching = [o for o in result if o.employee.pk == self.year_emp.pk]
        self.assertEqual(len(matching), 1)
        self.assertEqual(matching[0].total_excess, 6)  # 16 - 10

    def test_unknown_scope_raises(self):
        with self.assertRaises(ValueError):
            calculate_overtime("hour")
