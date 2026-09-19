import zipfile
from datetime import datetime

from django.core.exceptions import ValidationError
from django.db import models


def template_upload_path(instance, filename: str) -> str:
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    ext = filename.rsplit(".", 1)[-1].lower()
    kind = instance.kind or "unknown"
    return f"templates_docx/{kind}/{ts}_{kind}.{ext}"


class DocumentTemplate(models.Model):
    """
    Загруженный .docx-шаблон. Тип (`kind`) — слаг из Python-реестра
    timetable.exports.kinds.

    Рабочим считается последний загруженный шаблон для данного kind
    (см. library.get_lastest_template). История версий сохраняется:
    старые записи остаются в БД, их можно скачать или вернуть, но
    при экспорте используется самая свежая.
    """
    kind = models.SlugField(
        max_length=32,
        verbose_name="Тип документа",
        help_text="Один из зарегистрированных кодов (см. exports/kinds.py).",
    )
    file = models.FileField(
        upload_to=template_upload_path,
        verbose_name="Файл шаблона (.docx)",
    )
    uploaded_by = models.ForeignKey(
        "auth.User",
        null=True, blank=True,
        on_delete=models.SET_NULL,
        verbose_name="Загрузил",
    )
    uploaded_at = models.DateTimeField(
        auto_now_add=True, verbose_name="Загружен",
    )
    comment = models.CharField(
        max_length=255, blank=True, verbose_name="Комментарий",
    )

    class Meta:
        verbose_name = "Шаблон документа"
        verbose_name_plural = "Шаблоны документов"
        ordering = ["kind", "-uploaded_at"]

    def __str__(self) -> str:
        return f"{self.kind} — {self.uploaded_at:%d.%m.%Y %H:%M}"

    def clean(self) -> None:
        super().clean()
        from timetable.exports.kinds import codes

        if self.kind and self.kind not in codes():
            raise ValidationError({
                "kind": (
                    f"Неизвестный тип документа: {self.kind!r}. "
                    f"Доступные: {', '.join(codes())}."
                ),
            })

        if self.file and not self.file.name.lower().endswith(".docx"):
            raise ValidationError("Поддерживается только формат .docx")

        if self.file:
            self._validate_docx()

    def _validate_docx(self) -> None:
        """
        Проверка, что файл — читаемый .docx.

        1. is_zipfile — быстрая отсечка не-zip содержимого.
        2. DocxTemplate(...).get_docx() — форсируем ленивую инициализацию
           docxtpl, ловим несовместимость версии и отсутствие
           word/document.xml.
        """
        self.file.seek(0)
        if not zipfile.is_zipfile(self.file):
            raise ValidationError(
                "Файл не является .docx (не zip-архив). "
                "Проверьте, что загрузили именно документ Word."
            )

        try:
            from docxtpl import DocxTemplate
            self.file.seek(0)
            DocxTemplate(self.file).get_docx()
        except Exception as e:
            raise ValidationError(f"Не удалось прочитать шаблон: {e}")
        finally:
            self.file.seek(0)