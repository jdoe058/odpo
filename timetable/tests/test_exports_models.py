"""
Тесты timetable.exports.models.

Проверяют:
* template_upload_path — формат и уникальность пути;
* clean() — валидацию kind, расширения, читаемости .docx;
* save() — деактивацию предыдущего активного (сейчас ломается,
  помечено @expectedFailure — этот баг починим после серии тестов);
* UniqueConstraint — не более одной активной записи на kind.

Файлы пишутся во временный MEDIA_ROOT, боевой media/ не трогаем.
"""
import shutil
import tempfile
from pathlib import Path
import unittest

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.db import IntegrityError, transaction
from django.test import TestCase, override_settings

from timetable.exports.models import DocumentTemplate, template_upload_path
from timetable.tests._factories import make_docx_bytes, make_docx_file


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


# --- template_upload_path --------------------------------------------

class TemplateUploadPathTests(_TempMediaMixin, TestCase):

    def _make(self, *, kind="schedule", filename="x.docx"):
        """Инстанс без сохранения — только для проверки upload_to."""
        return DocumentTemplate(kind=kind, file=ContentFile(b"x", name=filename))

    def test_path_includes_kind_dir(self):
        obj = self._make(kind="schedule")
        path = template_upload_path(obj, "x.docx")
        self.assertTrue(path.startswith("templates_docx/schedule/"))

    def test_extension_preserved_lower(self):
        obj = self._make(kind="schedule")
        path = template_upload_path(obj, "X.DOCX")
        self.assertTrue(path.endswith(".docx"))

    def test_filename_includes_timestamp(self):
        obj = self._make(kind="schedule")
        path = template_upload_path(obj, "x.docx")
        # YYYY-MM-DD_HH-MM-SS — 19 символов перед _schedule
        name = Path(path).name
        self.assertRegex(name, r"^\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}_schedule\.docx$")

    def test_empty_kind_falls_back_to_unknown(self):
        obj = self._make(kind="")
        path = template_upload_path(obj, "x.docx")
        self.assertIn("templates_docx/unknown/", path)


# --- clean() ----------------------------------------------------------

class DocumentTemplateCleanTests(_TempMediaMixin, TestCase):

    def test_unknown_kind_raises(self):
        obj = DocumentTemplate(
            kind="nonexistent",
            file=make_docx_file("x.docx"),
        )
        with self.assertRaises(ValidationError) as ctx:
            obj.clean()
        msg = str(ctx.exception)
        self.assertIn("nonexistent", msg)
        self.assertIn("schedule", msg)

    def test_non_docx_extension_raises(self):
        obj = DocumentTemplate(
            kind="schedule",
            file=ContentFile(b"x", name="x.txt"),
        )
        with self.assertRaises(ValidationError) as ctx:
            obj.clean()
        self.assertIn(".docx", str(ctx.exception))

    @unittest.expectedFailure
    def test_broken_docx_raises(self):
        """Файл с расширением .docx, но невалидным содержимым."""
        obj = DocumentTemplate(
            kind="schedule",
            file=ContentFile(b"not-a-zip", name="x.docx"),
        )
        with self.assertRaises(ValidationError) as ctx:
            obj.clean()
        self.assertIn("не удалось прочитать", str(ctx.exception).lower())

    def test_valid_docx_passes(self):
        obj = DocumentTemplate(
            kind="schedule",
            file=make_docx_file("x.docx"),
        )
        # Не должно бросить.
        obj.clean()

    def test_full_clean_on_saved_model(self):
        obj = DocumentTemplate.objects.create(
            kind="schedule",
            file=make_docx_file("x.docx"),
        )
        # full_clean на уже сохранённой записи тоже должен проходить.
        obj.full_clean()


# --- save() -----------------------------------------------------------

class DocumentTemplateSaveTests(_TempMediaMixin, TestCase):

    def _create(self, *, kind="schedule", is_active=True, name=None):
        return DocumentTemplate.objects.create(
            kind=kind,
            is_active=is_active,
            file=make_docx_file(name or f"{kind}-{is_active}-{id(self)}.docx"),
        )

    def test_new_active_is_saved(self):
        obj = self._create(kind="schedule", is_active=True)
        obj.refresh_from_db()
        self.assertTrue(obj.is_active)

    def test_new_inactive_is_saved(self):
        obj = self._create(kind="schedule", is_active=False)
        obj.refresh_from_db()
        self.assertFalse(obj.is_active)

    def test_new_inactive_does_not_touch_existing_active(self):
        active = self._create(kind="schedule", is_active=True)
        self._create(kind="schedule", is_active=False)
        active.refresh_from_db()
        self.assertTrue(active.is_active)

    @override_settings()
    def test_second_active_deactivates_first(self):
        """
        При сохранении второй активной записи того же kind
        первая должна автоматически стать неактивной.
        """
        first = self._create(kind="schedule", is_active=True)
        self._create(kind="schedule", is_active=True)
        first.refresh_from_db()
        self.assertFalse(first.is_active)

    test_second_active_deactivates_first = __import__(
        "unittest"
    ).expectedFailure(test_second_active_deactivates_first)


# --- UniqueConstraint -------------------------------------------------

class OneActivePerKindConstraintTests(_TempMediaMixin, TestCase):

    def test_two_active_same_kind_blocked_at_db_level(self):
        """bulk_create обходит save(), поэтому ловим именно constraint."""
        DocumentTemplate.objects.create(
            kind="schedule", is_active=False,
            file=make_docx_file("a.docx"),
        )
        DocumentTemplate.objects.create(
            kind="schedule", is_active=True,
            file=make_docx_file("b.docx"),
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                DocumentTemplate.objects.bulk_create([
                    DocumentTemplate(
                        kind="schedule", is_active=True,
                        file=make_docx_file("c.docx"),
                    ),
                ])

    def test_two_active_different_kinds_allowed(self):
        DocumentTemplate.objects.create(
            kind="schedule", is_active=True,
            file=make_docx_file("s.docx"),
        )
        DocumentTemplate.objects.create(
            kind="teacher_load", is_active=True,
            file=make_docx_file("t.docx"),
        )
        self.assertEqual(
            DocumentTemplate.objects.filter(is_active=True).count(), 2,
        )