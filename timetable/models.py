import re
from django.db.models import Sum
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
    """
    Приводит ФИО к виду «ФАМИЛИЯ И.И.»:
    - верхний регистр;
    - схлопывание повторных пробелов;
    - убирает повторные точки и пробелы между инициалами;
    - добавляет точку после инициала, если её забыли.
    """
    if not value:
        return value

    value = re.sub(r"\s+", " ", str(value).strip()).upper()
    parts = value.split(" ")

    last_name = parts[0]
    # Всё после фамилии — инициалы: "И. И." → "ИИ"
    initials_letters = re.sub(r"[^А-ЯЁA-Z]", "", "".join(parts[1:]))

    if not initials_letters:
        return last_name

    return last_name + " " + "".join(f"{ch}." for ch in initials_letters)

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
        validate_short_name(self.short_name)

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

# --- Модели из подпакетов -------------------------------------------------
# Django находит модели только в <app>/models.py. DocumentTemplate
# физически живёт в timetable/exports/models.py, но регистрируется
# под app_label="timetable" — именно потому, что этот файл её импортирует.
from .exports.models import DocumentTemplate  # noqa: F401, E402