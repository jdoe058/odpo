"""
Тесты timetable.exports.library.

Проверяют:
* get_latest_template — выбор свежего шаблона, Http404 на отсутствующем;
* template_status — одну запись на каждый зарегистрированный kind;
* seed_templates — копирование эталонных .docx из репозитория в MEDIA_ROOT.

Реальные seed_templates/ (schedule.docx, teacher_load.docx, timesheet.docx)
не модифицируются — только читаются. MEDIA_ROOT изолирован.
"""
import shutil
import tempfile
from datetime import datetime, timezone

from django.http import Http404
from django.test import TestCase, override_settings

from timetable.exports.kinds import all_specs
from timetable.exports.library import (
    SEED_TEMPLATES_DIR, get_latest_template, seed_templates, template_status,
)
from timetable.exports.models import DocumentTemplate
from timetable.tests._factories import make_docx_file


class _TempMediaMixin:
    """Изолированный MEDIA_ROOT на класс."""

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


def _create_template(*, kind: str, when: datetime, name: str) -> DocumentTemplate:
    """
    Создаёт запись и явно выставляет uploaded_at.

    auto_now_add нельзя переопределить при create() — приходим через
    update(), минуя save(), чтобы auto_now_add не перезаписал значение.
    Нужно для тестов «свежий vs старый»: без разнесения дат порядок
    в БД недетерминирован.
    """
    tpl = DocumentTemplate.objects.create(
        kind=kind, file=make_docx_file(name),
    )
    DocumentTemplate.objects.filter(pk=tpl.pk).update(uploaded_at=when)
    tpl.refresh_from_db()
    return tpl


# --- get_latest_template ---------------------------------------------

class GetLatestTemplateTests(_TempMediaMixin, TestCase):

    def test_returns_latest(self):
        old = _create_template(
            kind="schedule", name="old.docx",
            when=datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc),
        )
        new = _create_template(
            kind="schedule", name="new.docx",
            when=datetime(2026, 2, 1, 10, 0, tzinfo=timezone.utc),
        )
        self.assertEqual(get_latest_template("schedule").pk, new.pk)
        self.assertNotEqual(get_latest_template("schedule").pk, old.pk)

    def test_raises_when_nothing(self):
        with self.assertRaises(Http404):
            get_latest_template("schedule")

    def test_does_not_confuse_kinds(self):
        sched = _create_template(
            kind="schedule", name="s.docx",
            when=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        _create_template(
            kind="teacher_load", name="t.docx",
            when=datetime(2026, 2, 1, tzinfo=timezone.utc),
        )
        self.assertEqual(get_latest_template("schedule").pk, sched.pk)


# --- template_status --------------------------------------------------

class TemplateStatusTests(_TempMediaMixin, TestCase):

    def test_one_row_per_registered_kind(self):
        rows = list(template_status())
        codes_expected = [s.code for s in all_specs()]
        codes_actual = [r["spec"].code for r in rows]
        self.assertEqual(codes_actual, codes_expected)

    def test_order_matches_all_specs(self):
        rows = template_status()
        specs = all_specs()
        for row, spec in zip(rows, specs):
            self.assertEqual(row["spec"].code, spec.code)

    def test_template_is_none_when_absent(self):
        for r in template_status():
            self.assertIsNone(r["template"])

    def test_template_is_latest(self):
        old = _create_template(
            kind="schedule", name="old.docx",
            when=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        new = _create_template(
            kind="schedule", name="new.docx",
            when=datetime(2026, 2, 1, tzinfo=timezone.utc),
        )
        by_code = {r["spec"].code: r["template"] for r in template_status()}
        self.assertEqual(by_code["schedule"].pk, new.pk)
        self.assertNotEqual(by_code["schedule"].pk, old.pk)
        self.assertIsNone(by_code["teacher_load"])
        self.assertIsNone(by_code["timesheet"])


# --- seed_templates ---------------------------------------------------

class SeedTemplatesTests(_TempMediaMixin, TestCase):

    def test_seed_files_present_in_repo(self):
        """
        В репо действительно лежат seed-файлы для всех зарегистрированных
        видов. Если кто-то удалит schedule.docx — тест сразу это покажет.
        """
        for spec in all_specs():
            self.assertTrue(
                (SEED_TEMPLATES_DIR / f"{spec.code}.docx").exists(),
                f"нет эталонного шаблона для {spec.code!r}",
            )

    def test_creates_template_for_all_kinds(self):
        result = seed_templates()
        created_codes = [code for code, created in result if created]
        self.assertEqual(
            sorted(created_codes), sorted(s.code for s in all_specs()),
        )
        for spec in all_specs():
            tpl = DocumentTemplate.objects.get(kind=spec.code)
            self.assertEqual(tpl.comment, "Эталонный шаблон из репозитория")
            self.assertTrue(tpl.file.name.startswith(f"templates_docx/{spec.code}/"))

    def test_idempotent(self):
        seed_templates()
        result = seed_templates()
        for _, created in result:
            self.assertFalse(created)
        self.assertEqual(
            DocumentTemplate.objects.count(),
            len(all_specs()),
        )

    def test_does_not_overwrite_existing(self):
        existing = DocumentTemplate.objects.create(
            kind="schedule", file=make_docx_file("custom.docx"),
        )
        result = seed_templates()
        flags = dict(result)
        self.assertFalse(flags["schedule"])
        self.assertEqual(
            DocumentTemplate.objects.filter(kind="schedule").count(), 1,
        )
        self.assertEqual(
            DocumentTemplate.objects.get(kind="schedule").pk, existing.pk,
        )

    def test_skips_kinds_without_seed_file(self):
        """
        Если у какого-то registered-кода нет файла в seed_templates/,
        он просто не попадает в результат. Принимаем как контракт.
        """
        result = seed_templates()
        codes_in_result = {code for code, _ in result}
        for code in codes_in_result:
            self.assertTrue((SEED_TEMPLATES_DIR / f"{code}.docx").exists())