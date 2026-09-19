"""
Тесты timetable.exports.views.export_view.

Проверяют:
* @login_required — аноним редиректится на login;
* 404 на неизвестный kind, отсутствующий цикл, отсутствующий шаблон;
* happy path для каждого зарегистрированного вида: 200, правильный
  Content-Type, non-empty zip/docx body, filename из build_filename спеки.

Шаблоны берём из реальных seed_templates/ через seed_templates() —
это то, что поедет в прод. MEDIA_ROOT изолирован.
"""
import shutil
import tempfile
from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse

from timetable.exports.base import DOCX_CONTENT_TYPE
from timetable.exports.kinds import all_specs
from timetable.exports.library import seed_templates
from timetable.tests._factories import (
    make_base, make_cycle, make_cycle_name,
    make_employee, make_funding_type, make_position,
)


class _TempMediaMixin:
    """Изолированный MEDIA_ROOT на класс тестов."""

    @classmethod
    def setUpClass(cls):
        cls._media_dir = tempfile.mkdtemp(prefix="timetable-test-media-")
        cls._override = override_settings(MEDIA_ROOT=cls._media_dir)
        cls._override.enable()
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        cls._override.disable()
        shutil.rmtree(cls._media_dir, ignore_errors=True)


# --- фикстуры цикла, общие для всех трёх классов ----------------------

def _make_test_cycle():
    """Собирает минимальный цикл с signer и approver — как в проде."""
    pos_signer = make_position(
        "зав. отделением", can_sign=True, sort_order=30,
    )
    pos_approver = make_position(
        "директор", can_approve=True, sort_order=10,
    )
    signer = make_employee("ИВАНОВ И.И.", pos_signer)
    make_employee("ПЕТРОВ П.П.", pos_approver)   # approver

    base = make_base("КОРПУС №1")
    funding = make_funding_type("БЮДЖЕТ")
    cname = make_cycle_name("ОХРАНА ТРУДА")
    return make_cycle(
        name=cname, base=base, funding=funding, compiled_by=signer,
        start_date=date(2026, 9, 1), end_date=date(2026, 9, 30),
    )


# --- доступ -----------------------------------------------------------

class ExportViewRequiresLoginTests(_TempMediaMixin, TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.cycle = _make_test_cycle()

    def test_anonymous_redirects_to_login(self):
        url = reverse(
            "timetable:cycle_export",
            args=[self.cycle.pk, "schedule"],
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)
        self.assertIn("next=", response.url)


# --- 404 --------------------------------------------------------------

class ExportViewErrorTests(_TempMediaMixin, TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.cycle = _make_test_cycle()

    def setUp(self):
        self.user = User.objects.create_user("tester", password="x")
        self.client.force_login(self.user)

    def _url(self, kind, cycle_id=None):
        return reverse(
            "timetable:cycle_export",
            args=[cycle_id or self.cycle.pk, kind],
        )

    def test_unknown_kind_returns_404(self):
        seed_templates()
        response = self.client.get(self._url("nonexistent"))
        self.assertEqual(response.status_code, 404)

    def test_missing_cycle_returns_404(self):
        seed_templates()
        response = self.client.get(self._url("schedule", cycle_id=999_999))
        self.assertEqual(response.status_code, 404)

    def test_no_template_returns_404(self):
        # seed_templates не вызываем — ни одного шаблона нет.
        response = self.client.get(self._url("schedule"))
        self.assertEqual(response.status_code, 404)


# --- happy path -------------------------------------------------------

class ExportViewHappyPathTests(_TempMediaMixin, TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.cycle = _make_test_cycle()

    def setUp(self):
        self.user = User.objects.create_user("tester", password="x")
        self.client.force_login(self.user)
        seed_templates()

    def _url(self, kind, cycle_id=None):
        return reverse(
            "timetable:cycle_export",
            args=[cycle_id or self.cycle.pk, kind],
        )

    def test_all_kinds_return_200(self):
        for spec in all_specs():
            with self.subTest(kind=spec.code):
                response = self.client.get(self._url(spec.code))
                self.assertEqual(
                    response.status_code, 200,
                    f"{spec.code}: ожидали 200, получили {response.status_code}",
                )

    def test_content_type_is_docx(self):
        for spec in all_specs():
            with self.subTest(kind=spec.code):
                response = self.client.get(self._url(spec.code))
                self.assertEqual(response["Content-Type"], DOCX_CONTENT_TYPE)

    def test_body_is_nonempty_zip(self):
        """docx — это zip. PK\\x03\\x04 — магическая подпись."""
        for spec in all_specs():
            with self.subTest(kind=spec.code):
                response = self.client.get(self._url(spec.code))
                self.assertGreater(len(response.content), 0)
                self.assertEqual(response.content[:2], b"PK")

    def test_content_disposition_has_attachment_and_utf8(self):
        for spec in all_specs():
            with self.subTest(kind=spec.code):
                response = self.client.get(self._url(spec.code))
                cd = response["Content-Disposition"]
                self.assertTrue(cd.startswith("attachment;"))
                self.assertIn("filename*=UTF-8''", cd)

    def test_filename_starts_with_spec_code(self):
        """
        Имя файла строит spec.build_filename(cycle). Префикс совпадает
        с code — так и задумано в schedule.py, teacher_load.py,
        timesheet.py.
        """
        for spec in all_specs():
            with self.subTest(kind=spec.code):
                response = self.client.get(self._url(spec.code))
                cd = response["Content-Disposition"]
                self.assertIn(spec.code, cd)

    def test_filename_cyrillic_is_encoded(self):
        """
        cycle.name.name = 'ОХРАНА ТРУДА' — в filename попадёт кириллица,
        quote() должна её закодировать. Сырых кириллических байт в
        заголовке быть не должно.
        """
        response = self.client.get(self._url("schedule"))
        cd = response["Content-Disposition"]
        self.assertNotIn("ОХРАНА", cd)
        self.assertNotIn("ТРУДА", cd)
        self.assertIn("%", cd)