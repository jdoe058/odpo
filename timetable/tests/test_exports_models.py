"""
Тесты timetable.exports.models.

Проверяют:
* template_upload_path — формат и уникальность пути;
* clean() — валидацию kind, расширения, читаемости .docx.

Файлы пишутся во временный MEDIA_ROOT, боевой media/ не трогаем.
"""
import io
import shutil
import tempfile
import zipfile
from pathlib import Path

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.test import TestCase, override_settings

from timetable.exports.models import DocumentTemplate, template_upload_path
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
        name = Path(path).name
        self.assertRegex(
            name, r"^\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}_schedule\.docx$",
        )

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

    def test_broken_docx_raises(self):
        """Не-zip содержимое с расширением .docx отклоняется."""
        obj = DocumentTemplate(
            kind="schedule",
            file=ContentFile(b"not-a-zip", name="x.docx"),
        )
        with self.assertRaises(ValidationError) as ctx:
            obj.clean()
        self.assertIn("не является .docx", str(ctx.exception).lower())

    def test_zip_without_document_xml_raises(self):
        """
        Zip-архив без word/document.xml — не .docx. Первая линия
        (is_zipfile) пропускает, вторая (DocxTemplate.get_docx)
        должна поймать.
        """
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("readme.txt", "это не документ Word")
        obj = DocumentTemplate(
            kind="schedule",
            file=ContentFile(buf.getvalue(), name="x.docx"),
        )
        with self.assertRaises(ValidationError) as ctx:
            obj.clean()
        self.assertIn("не удалось прочитать", str(ctx.exception).lower())

    def test_valid_docx_passes(self):
        obj = DocumentTemplate(
            kind="schedule",
            file=make_docx_file("x.docx"),
        )
        obj.clean()  # не должно бросить

    def test_full_clean_on_saved_model(self):
        obj = DocumentTemplate.objects.create(
            kind="schedule",
            file=make_docx_file("x.docx"),
        )
        obj.full_clean()