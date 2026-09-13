import re

from django.core.exceptions import ValidationError
from django.db import models


# Формат "ФАМИЛИЯ И.И." в верхнем регистре.
# Допускает дефисы и апострофы в фамилии.
SHORT_NAME_RE = re.compile(
    r"^[А-ЯЁA-Z][А-ЯЁA-Z\-']+(\s[А-ЯЁA-Z]\.(\s?[А-ЯЁA-Z]\.)?)?$"
)

def normalize_name(value) -> str:
    """Схлопывает пробелы и приводит к верхнему регистру."""
    return " ".join(str(value or "").split()).upper()

def normalize_short_name(value: str) -> str:
    """Верхний регистр + нормализация пробелов."""
    if not value:
        return value
    value = value.strip()
    value = re.sub(r"\s+", " ", value)
    return value.upper()

def validate_short_name(value: str) -> None:
    """Проверить формат после нормализации."""
    if not SHORT_NAME_RE.match(value):
        raise ValidationError(
            "Укажите фамилию и инициалы в верхнем регистре, например: ИВАНОВ И.И."
        )

class Position(models.Model):
    """Должность сотрудника."""

    name = models.CharField("Название", max_length=100, unique=True)

    max_hours_per_day = models.PositiveSmallIntegerField(
        "Макс. часов в день",
        default=0,
        help_text="0 — сотрудник не ведёт занятия.",
    )
    can_sign = models.BooleanField(
        "Подписывает расписание",
        default=False,
        help_text="Например, зав. отделением.",
    )
    can_approve = models.BooleanField(
        "Утверждает расписание",
        default=False,
        help_text="Например, зам. директора по ДПО.",
    )
    sort_order = models.PositiveSmallIntegerField(
        "Порядок сортировки",
        default=100,
    )

    class Meta:
        verbose_name = "Должность"
        verbose_name_plural = "Должности"
        ordering = ["sort_order", "name"]

    def __str__(self) -> str:
        return self.name

    @property
    def can_teach(self) -> bool:
        return self.max_hours_per_day > 0

class Employee(models.Model):
    """Сотрудник."""

    short_name = models.CharField(
        "Короткое имя",
        max_length=50,
        unique=True,
        validators=[validate_short_name],
        help_text="Фамилия и инициалы, например: ИВАНОВ И.И. "
                  "Регистр и пробелы нормализуются автоматически.",
    )
    position = models.ForeignKey(
        Position,
        on_delete=models.PROTECT,
        related_name="employees",
        verbose_name="Должность",
    )

    class Meta:
        verbose_name = "Сотрудник"
        verbose_name_plural = "Сотрудники"
        ordering = ["short_name"]

    def __str__(self) -> str:
        return f"{self.short_name} ({self.position.name})"

    def clean(self) -> None:
        super().clean()
        self.short_name = normalize_short_name(self.short_name)

    def save(self, *args, **kwargs):
        self.short_name = normalize_short_name(self.short_name)
        super().save(*args, **kwargs)

    # Прокси-свойства на должность
    @property
    def max_hours_per_day(self) -> int:
        return self.position.max_hours_per_day

    @property
    def can_teach(self) -> bool:
        return self.position.can_teach

    @property
    def can_sign(self) -> bool:
        return self.position.can_sign

    @property
    def can_approve(self) -> bool:
        return self.position.can_approve

class Base(models.Model):
    name = models.CharField(
        max_length=255,
        unique=True,
        verbose_name="Название базы"
    )

    class Meta:
        verbose_name = "База"
        verbose_name_plural = "Базы"
        ordering = ["name"]

    def __str__(self):
        return self.name

class LessonType(models.Model):
    class Category(models.TextChoices):
        LECTURE = "lecture", "Лекции"
        SEMINAR = "seminar", "Занятия семинарского типа"
        PRACTICE = "practice", "Практика"

    name = models.CharField(max_length=255, unique=True, verbose_name="Название")
    code = models.CharField(max_length=20, unique=True, verbose_name="Код")
    sort_order = models.PositiveIntegerField(unique=True, verbose_name="Порядок сортировки")
    counts_in_hours = models.BooleanField(default=True, verbose_name="Участвует в подсчёте часов")
    category = models.CharField(
        max_length=20,
        choices=Category.choices,
        blank=True,
        verbose_name="Категория в отчёте",
        help_text=(
            "Используется в отчёте «Распределение часов преподавателей». "
            "Оставьте пустым, если тип занятия не должен попадать в этот отчёт "
            "(например, экзамен или консультация)."
        ),
    )

    class Meta:
        verbose_name = "Тип занятия"
        verbose_name_plural = "Типы занятий"
        ordering = ["sort_order"]

    def __str__(self):
        return f"{self.code} — {self.name}"

class FundingType(models.Model):
    name = models.CharField(
        max_length=255,
        unique=True,
        verbose_name="Название"
    )

    class Meta:
        verbose_name = "Вид финансирования"
        verbose_name_plural = "Виды финансирования"
        ordering = ["name"]

    def __str__(self):
        return self.name

class CycleName(models.Model):
    name = models.CharField(
        max_length=255,
        unique=True,
        verbose_name="Название"
    )

    class Meta:
        verbose_name = "Название цикла"
        verbose_name_plural = "Названия циклов"
        ordering = ["name"]

    def __str__(self):
        return self.name

class Cycle(models.Model):
    name = models.ForeignKey(
        CycleName, on_delete=models.PROTECT,
        related_name="cycles", verbose_name="Название цикла",
    )
    funding_type = models.ForeignKey(
        FundingType, on_delete=models.PROTECT,
        related_name="cycles", verbose_name="Вид финансирования",
    )
    base = models.ForeignKey(
        Base, on_delete=models.PROTECT,
        related_name="cycles", verbose_name="База",
    )
    start_date = models.DateField(verbose_name="Дата начала")
    end_date = models.DateField(verbose_name="Дата окончания")

    compiled_by = models.ForeignKey(
        "Employee",
        on_delete=models.PROTECT,
        related_name="compiled_cycles",
        verbose_name="Составил",
    )

    class Meta:
        verbose_name = "Цикл"
        verbose_name_plural = "Циклы"
        ordering = ["-start_date", "name"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(end_date__gte=models.F("start_date")),
                name="cycle_end_after_start",
            ),
        ]

    def clean(self):
        super().clean()
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValidationError({
                "end_date": "Дата окончания не может быть раньше даты начала."
            })

    @property
    def total_hours(self):
        """Сумма часов по занятиям, у типов которых counts_in_hours=True."""
        return (
            self.lessons
            .filter(lesson_type__counts_in_hours=True)
            .aggregate(total=Sum("hours"))["total"]
            or 0
        )

    def __str__(self):
        return f"{self.name} ({self.start_date:%d.%m.%Y} — {self.end_date:%d.%m.%Y})"

class Lesson(models.Model):
    cycle = models.ForeignKey(
        Cycle, on_delete=models.CASCADE,
        related_name="lessons", verbose_name="Цикл",
    )
    date = models.DateField(verbose_name="Дата")
    time_start = models.TimeField(verbose_name="Начало")
    time_end = models.TimeField(verbose_name="Окончание")
    hours = models.PositiveSmallIntegerField(verbose_name="Часы")
    lesson_type = models.ForeignKey(
        LessonType, on_delete=models.PROTECT,
        related_name="lessons", verbose_name="Тип занятия",
    )
    topic = models.CharField(
        max_length=255, blank=True, verbose_name="Тема",
    )
    employee = models.ForeignKey(
        Employee, on_delete=models.PROTECT,
        related_name="lessons", verbose_name="Преподаватель",
    )

    class Meta:
        verbose_name = "Занятие"
        verbose_name_plural = "Занятия"
        ordering = ["date", "time_start"]

    def __str__(self):
        return f"{self.date:%d.%m.%Y} {self.time_start:%H:%M} — {self.employee}"

def template_upload_path(instance, filename):
    # templates_docx/schedule/2026-09-13_15-30-00_schedule.docx
    from datetime import datetime
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    ext = filename.rsplit(".", 1)[-1].lower()
    return f"templates_docx/{instance.kind}/{ts}_{instance.kind}.{ext}"

class DocumentKind(models.Model):
    code = models.SlugField(
        max_length=32, unique=True,
        verbose_name="Код",
        help_text="Латиницей, без пробелов. Например: schedule, teacher_load.",
    )
    name = models.CharField(
        max_length=100, unique=True, verbose_name="Название",
    )
    sort_order = models.PositiveIntegerField(
        default=100, verbose_name="Порядок сортировки",
    )

    class Meta:
        verbose_name = "Тип документа"
        verbose_name_plural = "Типы документов"
        ordering = ["sort_order", "name"]

    def __str__(self):
        return self.name

    def clean(self):
        super().clean()
        self.code = self.code.strip().lower().replace(" ", "_")

class DocumentTemplate(models.Model):
    class Kind(models.TextChoices):
        SCHEDULE = "schedule", "Расписание цикла"
        LOAD_SUMMARY = "load_summary", "Сводка нагрузки"
        # добавляй сюда по мере появления новых выгрузок

    kind = models.ForeignKey(DocumentKind, on_delete=models.PROTECT, null=False) 

    file = models.FileField(
        upload_to=template_upload_path,
        verbose_name="Файл шаблона (.docx)",
    )
    is_active = models.BooleanField(
        default=True, verbose_name="Активный",
        help_text="Используется для выгрузки. Для каждого типа активен только один.",
    )
    uploaded_by = models.ForeignKey(
        "auth.User", null=True, blank=True,
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

    def __str__(self):
        status = "активен" if self.is_active else "архив"
        kind = self.kind.name if self.kind_id else "—"
        return f"{kind} — {self.uploaded_at:%d.%m.%Y} ({status})"

    def clean(self):
        super().clean()
        if self.file and not self.file.name.lower().endswith(".docx"):
            raise ValidationError("Поддерживается только формат .docx")
        # пробуем открыть — чтобы отловить битый файл сразу
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
            # гасим остальные активные шаблоны этого типа
            DocumentTemplate.objects.filter(
                kind=self.kind, is_active=True
            ).exclude(pk=self.pk).update(is_active=False)