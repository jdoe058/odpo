"""
Тесты timetable.exports.kinds.

Проверяют:
* реестр: register / get / all_specs / codes;
* сборку общего контекста выгрузки (build_common_context);
* слияние общего и специфичного контекстов в ExporterSpec.build_context.

Реестр — глобальный объект, наполняется в apps.ready(). Тесты на
register() работают поверх пустого реестра через patch.dict, чтобы
не портить состояние соседних тестов.
"""
from datetime import date
from unittest.mock import patch

from django.test import SimpleTestCase, TestCase

from timetable.exports.kinds import (
    ExporterSpec, all_specs, build_common_context, codes, get, register,
)
from timetable.models import Employee
from timetable.tests._factories import (
    make_base, make_cycle, make_cycle_name, make_employee,
    make_funding_type, make_position,
)


# --- helpers ----------------------------------------------------------

def _spec(code, *, name="Тест", sort_order=100, own=None, filename="f.docx"):
    """
    Быстрая сборка ExporterSpec для тестов реестра.
    own — функция build_own_context; по умолчанию пустая.
    """
    return ExporterSpec(
        code=code,
        name=name,
        sort_order=sort_order,
        build_own_context=own or (lambda cycle: {}),
        build_filename=(
            filename if callable(filename) else (lambda cycle: filename)
        ),
    )


# --- реестр -----------------------------------------------------------

class RegistryTests(SimpleTestCase):
    """Реестр зарегистрированных выгрузок."""

    def test_standard_kinds_registered(self):
        """apps.ready() наполнил реестр тремя стандартными видами."""
        known = set(codes())
        for code in ("schedule", "teacher_load", "timesheet"):
            self.assertIn(code, known, f"{code!r} отсутствует в реестре")

    def test_get_returns_spec(self):
        spec = get("schedule")
        self.assertIsInstance(spec, ExporterSpec)
        self.assertEqual(spec.code, "schedule")

    def test_get_unknown_raises_key_error(self):
        with self.assertRaises(KeyError) as ctx:
            get("nonexistent")
        # В сообщении должно быть и имя неизвестного кода,
        # и список известных — иначе отладка мучительна.
        msg = str(ctx.exception)
        self.assertIn("nonexistent", msg)
        self.assertIn("schedule", msg)

    def test_all_specs_sorted_by_sort_order_then_name(self):
        specs = all_specs()
        keys = [(s.sort_order, s.name) for s in specs]
        self.assertEqual(keys, sorted(keys))

    def test_codes_matches_all_specs_order(self):
        self.assertEqual(codes(), [s.code for s in all_specs()])

    def test_register_adds_spec(self):
        with patch.dict("timetable.exports.kinds._REGISTRY", {}, clear=True):
            spec = _spec("test_kind")
            register(spec)
            self.assertEqual(get("test_kind"), spec)

    def test_register_duplicate_raises(self):
        with patch.dict("timetable.exports.kinds._REGISTRY", {}, clear=True):
            register(_spec("dup"))
            with self.assertRaises(ValueError) as ctx:
                register(_spec("dup"))
            self.assertIn("dup", str(ctx.exception))

    def test_register_returns_same_spec(self):
        """Декораторный контракт register(spec) -> spec."""
        with patch.dict("timetable.exports.kinds._REGISTRY", {}, clear=True):
            spec = _spec("test_kind")
            self.assertIs(register(spec), spec)


# --- build_common_context --------------------------------------------

class BuildCommonContextTests(TestCase):
    """Поля, общие для всех выгрузок."""

    @classmethod
    def setUpTestData(cls):
        cls.pos_teacher = make_position("преподаватель", can_sign=True)
        cls.pos_chief = make_position(
            "директор", can_approve=True, sort_order=10,
        )
        cls.teacher = make_employee("ИВАНОВ И.И.", cls.pos_teacher)
        cls.chief = make_employee("ПЕТРОВ П.П.", cls.pos_chief)

        cls.base = make_base("КОРПУС №1")
        cls.funding = make_funding_type("БЮДЖЕТ")
        cls.cname = make_cycle_name("ОХРАНА ТРУДА")
        cls.cycle = make_cycle(
            name=cls.cname, base=cls.base, funding=cls.funding,
            compiled_by=cls.teacher,
            start_date=date(2026, 9, 1), end_date=date(2026, 9, 30),
        )

    def test_all_fields(self):
        ctx = build_common_context(self.cycle)
        self.assertEqual(ctx["cycle_name"], "ОХРАНА ТРУДА")
        self.assertEqual(ctx["funding"], "БЮДЖЕТ")
        self.assertEqual(ctx["base"], "КОРПУС №1")
        self.assertEqual(ctx["start"], "01.09.2026")
        self.assertEqual(ctx["end"], "30.09.2026")
        self.assertEqual(ctx["signer"], "ИВАНОВ И.И.")
        self.assertEqual(ctx["signer_position"], "преподаватель")
        self.assertEqual(ctx["approver"], "ПЕТРОВ П.П.")
        self.assertEqual(ctx["approver_position"], "директор")

    def test_dates_format(self):
        ctx = build_common_context(self.cycle)
        for key in ("start", "end"):
            self.assertRegex(ctx[key], r"^\d{2}\.\d{2}\.\d{4}$")

    def test_no_approver_in_db(self):
        """
        Если в БД нет ни одного сотрудника с can_approve=True —
        контекст содержит пустые строки, а не None и не падает.
        """
        Employee.objects.filter(position__can_approve=True).delete()
        ctx = build_common_context(self.cycle)
        self.assertEqual(ctx["approver"], "")
        self.assertEqual(ctx["approver_position"], "")


# --- ExporterSpec.build_context --------------------------------------

class ExporterSpecBuildContextTests(TestCase):
    """Слияние common + own в ExporterSpec.build_context."""

    @classmethod
    def setUpTestData(cls):
        pos = make_position("преподаватель")
        cls.emp = make_employee("ИВАНОВ И.И.", pos)
        cls.base = make_base("КОРПУС")
        cls.funding = make_funding_type("БЮДЖЕТ")
        cls.cname = make_cycle_name("ЦИКЛ")
        cls.cycle = make_cycle(
            name=cls.cname, base=cls.base, funding=cls.funding,
            compiled_by=cls.emp,
            start_date=date(2026, 9, 1), end_date=date(2026, 9, 30),
        )

    def test_own_context_merged(self):
        spec = _spec("test", own=lambda cycle: {"own_field": "value"})
        ctx = spec.build_context(self.cycle)
        self.assertEqual(ctx["own_field"], "value")
        # И общие поля на месте.
        self.assertIn("cycle_name", ctx)
        self.assertIn("signer", ctx)

    def test_own_overrides_common(self):
        spec = _spec("test", own=lambda cycle: {"cycle_name": "OVERRIDDEN"})
        ctx = spec.build_context(self.cycle)
        self.assertEqual(ctx["cycle_name"], "OVERRIDDEN")

    def test_build_context_does_not_mutate_own(self):
        """
        build_context возвращает новый dict, а не мутирует
        возвращаемое build_own_context. Полезно знать, если
        кто-то закэширует результат.
        """
        own = {"own_field": "value"}
        spec = _spec("test", own=lambda cycle: dict(own))
        spec.build_context(self.cycle)
        self.assertEqual(own, {"own_field": "value"})