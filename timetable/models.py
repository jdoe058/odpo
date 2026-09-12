import re

from django.core.exceptions import ValidationError
from django.db import models


# Формат "ФАМИЛИЯ И.И." в верхнем регистре.
# Допускает дефисы и апострофы в фамилии.
SHORT_NAME_RE = re.compile(
    r"^[А-ЯЁA-Z][А-ЯЁA-Z\-']+(\s[А-ЯЁA-Z]\.(\s?[А-ЯЁA-Z]\.)?)?$"
)


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
    name = models.CharField(
        max_length=255,
        unique=True,
        verbose_name="Название"
    )
    code = models.CharField(
        max_length=20,
        unique=True,
        verbose_name="Код"
    )
    sort_order = models.PositiveIntegerField(
        unique=True,
        verbose_name="Порядок сортировки"
    )
    counts_in_hours = models.BooleanField(
        default=True,
        verbose_name="Участвует в подсчёте часов"
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
        CycleName,
        on_delete=models.PROTECT,
        related_name="cycles",
        verbose_name="Название цикла"
    )
    start_date = models.DateField(
        verbose_name="Дата начала"
    )
    end_date = models.DateField(
        verbose_name="Дата окончания"
    )
    approved_by = models.ForeignKey(
        "Employee",
        on_delete=models.PROTECT,
        related_name="approved_cycles",
        limit_choices_to={"position__can_approve": True},
        verbose_name="Утвердил"
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
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValidationError({
                "end_date": "Дата окончания не может быть раньше даты начала."
            })
        if self.approved_by_id and not self.approved_by.can_approve:
            raise ValidationError({
                "approved_by": "Выбранный сотрудник не имеет права утверждать циклы."
            })

    def __str__(self):
        return f"{self.name} ({self.start_date:%d.%m.%Y} — {self.end_date:%d.%m.%Y})"

