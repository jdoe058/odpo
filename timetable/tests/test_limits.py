from datetime import date, time
from types import SimpleNamespace

from django.test import TestCase

from timetable.models import (
    Base, Cycle, CycleName, Employee, FundingType, Lesson, LessonType,
    Position,
)
from timetable.services.limits import (
    SCOPES, calculate_overtime, find_violations, format_violation,
)

def _stub(*, employee, d, hours=2, lesson_type):
    """Псевдо-Lesson для find_violations (в БД не сохраняется)."""
    return SimpleNamespace(
        date=d, hours=hours, employee=employee, lesson_type=lesson_type,
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

class FindViolationsDayTests(LimitsBase):
    def test_under_limit(self):
        v = find_violations(
            [_stub(employee=self.teacher, d=date(2026, 9, 1),
                   hours=4, lesson_type=self.lt_lecture)],
            scope="day",
        )
        self.assertEqual(v, ())

    def test_exactly_at_limit(self):
        v = find_violations(
            [_stub(employee=self.teacher, d=date(2026, 9, 1),
                   hours=6, lesson_type=self.lt_lecture)],
            scope="day",
        )
        self.assertEqual(v, ())

    def test_over_limit(self):
        v = find_violations(
            [_stub(employee=self.teacher, d=date(2026, 9, 1),
                   hours=8, lesson_type=self.lt_lecture)],
            scope="day",
        )
        self.assertEqual(len(v), 1)
        self.assertEqual(v[0].scope, "day")
        self.assertEqual(v[0].hours, 8)
        self.assertEqual(v[0].limit, 6)
        self.assertEqual(v[0].excess, 2)

    def test_ignores_non_counting_types(self):
        v = find_violations(
            [_stub(employee=self.teacher, d=date(2026, 9, 1),
                   hours=100, lesson_type=self.lt_exam)],
            scope="day",
        )
        self.assertEqual(v, ())

    def test_ignores_employee_without_limit(self):
        v = find_violations(
            [_stub(employee=self.chief, d=date(2026, 9, 1),
                   hours=100, lesson_type=self.lt_lecture)],
            scope="day",
        )
        self.assertEqual(v, ())

    def test_accumulates_db_and_new(self):
        self._db_lesson(d=date(2026, 9, 1), hours=4)
        v = find_violations(
            [_stub(employee=self.teacher, d=date(2026, 9, 1),
                   hours=4, lesson_type=self.lt_lecture)],
            scope="day",
        )
        self.assertEqual(len(v), 1)
        self.assertEqual(v[0].hours, 8)

class FindViolationsWeekTests(LimitsBase):
    def test_week_over_limit(self):
        # 7 дней × 6 ч = 42 ч > 36 ч/нед
        new = [
            _stub(employee=self.teacher, d=date(2026, 9, 7 + i),
                  hours=6, lesson_type=self.lt_lecture)
            for i in range(7)
        ]
        v = find_violations(new, scope="week")
        self.assertEqual(len(v), 1)
        self.assertEqual(v[0].hours, 42)
        self.assertEqual(v[0].limit, 36)
        self.assertEqual(v[0].period_start, date(2026, 9, 7))
        self.assertEqual(v[0].period_end, date(2026, 9, 13))

    def test_split_across_weeks_not_combined(self):
        new = [
            _stub(employee=self.teacher, d=date(2026, 9, 7),
                  hours=6, lesson_type=self.lt_lecture),
            _stub(employee=self.teacher, d=date(2026, 9, 14),
                  hours=6, lesson_type=self.lt_lecture),
        ]
        self.assertEqual(find_violations(new, scope="week"), ())

class FindViolationsYearTests(LimitsBase):
    def test_year_over_limit(self):
        v = find_violations(
            [_stub(employee=self.year_emp, d=date(2026, 12, 1),
                   hours=12, lesson_type=self.lt_lecture)],
            scope="year",
        )
        self.assertEqual(len(v), 1)
        self.assertEqual(v[0].period_start, date(2026, 9, 1))
        self.assertEqual(v[0].period_end, date(2027, 8, 31))

    def test_year_boundary_not_combined(self):
        # 31.08.2026 и 01.09.2026 — разные учебные годы;
        # 8 + 8 = 16 не должно суммироваться в один год.
        aug = _stub(employee=self.year_emp, d=date(2026, 8, 31),
                    hours=8, lesson_type=self.lt_lecture)
        sep = _stub(employee=self.year_emp, d=date(2026, 9, 1),
                    hours=8, lesson_type=self.lt_lecture)
        self.assertEqual(find_violations([aug, sep], scope="year"), ())

class FindViolationsExclusionTests(LimitsBase):
    def test_exclude_cycle_id(self):
        self._db_lesson(d=date(2026, 9, 1), hours=6)
        new = [_stub(employee=self.teacher, d=date(2026, 9, 1),
                     hours=6, lesson_type=self.lt_lecture)]
        # Без исключения: 6 (БД) + 6 (новое) = 12 > 6.
        self.assertEqual(len(find_violations(new, scope="day")), 1)
        # С исключением цикла: остаётся только новое = 6 ≤ 6.
        self.assertEqual(
            find_violations(new, scope="day",
                            exclude_cycle_id=self.cycle.pk),
            (),
        )

    def test_exclude_lesson_ids(self):
        existing = self._db_lesson(d=date(2026, 9, 1), hours=6)
        new = [_stub(employee=self.teacher, d=date(2026, 9, 1),
                     hours=6, lesson_type=self.lt_lecture)]
        self.assertEqual(len(find_violations(new, scope="day")), 1)
        self.assertEqual(
            find_violations(new, scope="day",
                            exclude_lesson_ids=(existing.pk,)),
            (),
        )

class FindViolationsAllTests(LimitsBase):
    def test_scope_all_day_only(self):
        new = [_stub(employee=self.teacher, d=date(2026, 9, 7),
                     hours=8, lesson_type=self.lt_lecture)]
        v = find_violations(new)  # scope="all" по умолчанию
        self.assertEqual([x.scope for x in v], ["day"])

    def test_scope_all_week_only(self):
        new = [
            _stub(employee=self.teacher, d=date(2026, 9, 7 + i),
                  hours=6, lesson_type=self.lt_lecture)
            for i in range(7)
        ]
        v = find_violations(new)
        self.assertEqual([x.scope for x in v], ["week"])
        self.assertEqual(v[0].hours, 42)

class FormatViolationTests(LimitsBase):
    def test_format_single_day(self):
        v = find_violations(
            [_stub(employee=self.teacher, d=date(2026, 9, 1),
                   hours=8, lesson_type=self.lt_lecture)],
            scope="day",
        )[0]
        msg = format_violation(v)
        self.assertIn("ИВАНОВ И.И.", msg)
        self.assertIn("01.09.2026", msg)
        self.assertIn("лимит 6", msg)

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
