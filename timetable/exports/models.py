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
    timetable.exports.kinds. Валидация по реестру в clean().
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
    is_active = models.BooleanField(
        default=True,
        verbose_name="Активный",
        help_text="Для каждого типа активен только один.",
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
        constraints = [
            # На уровне БД гарантируем: не более одного активного
            # шаблона на каждый тип. save() тоже это делает, но
            # constraint страхует от гонок и admin bulk-операций.
            models.UniqueConstraint(
                fields=["kind"],
                condition=models.Q(is_active=True),
                name="one_active_template_per_kind",
            ),
        ]

    def __str__(self) -> str:
        status = "активен" if self.is_active else "архив"
        return f"{self.kind} — {self.uploaded_at:%d.%m.%Y} ({status})"

    def clean(self) -> None:
        super().clean()
        # Локальный импорт: реестр наполняется в apps.ready(),
        # а clean() может вызываться и раньше (например, из shell).
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
            try:
                from docxtpl import DocxTemplate
                self.file.seek(0)
                DocxTemplate(self.file)
                self.file.seek(0)
            except Exception as e:
                raise ValidationError(f"Не удалось прочитать шаблон: {e}")

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.is_active:
            DocumentTemplate.objects.filter(
                kind=self.kind, is_active=True,
            ).exclude(pk=self.pk).update(is_active=False)
