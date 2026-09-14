from io import BytesIO
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from timetable.models import (
    Base, CycleName, Employee, FundingType, LessonType, Position,
)
from timetable.imports import ScheduleImportError, import_schedule
from timetable.imports.discovery import DiscoveredReferences, discover_references


class Command(BaseCommand):
    help = (
        "Загрузить расписание из XLSX. Если в файле упомянуты сущности, "
        "которых нет в БД, команда спрашивает, добавлять ли их."
    )

    def add_arguments(self, parser):
        parser.add_argument("path", type=Path, help="Путь к XLSX-файлу")
        parser.add_argument(
            "--no-input",
            action="store_true",
            help="Не задавать вопросов. При отсутствующих сущностях — отменить импорт.",
        )

    # ------------------------------------------------------------------ run

    def handle(self, *args, **opts):
        path: Path = opts["path"]
        if not path.exists():
            raise CommandError(f"Файл не найден: {path}")

        data = path.read_bytes()

        try:
            refs = discover_references(data)
        except Exception as e:
            raise CommandError(f"Не удалось прочитать файл: {e}")

        missing = self._collect_missing(refs)

        if missing:
            self._report_missing(missing)
            if opts["no_input"]:
                raise CommandError(
                    "Обнаружены отсутствующие сущности, "
                    "а --no-input запрещает их создавать."
                )
            if not self._create_all(missing):
                raise CommandError("Импорт отменён.")

        try:
            result = import_schedule(BytesIO(data))
        except ScheduleImportError as e:
            self.stderr.write(self.style.ERROR("Импорт не выполнен:"))
            for err in e.errors:
                self.stderr.write(f"  • {err}")
            raise CommandError("Исправьте ошибки в файле и повторите.")

        self.stdout.write(self.style.SUCCESS(
            f"Импортировано занятий: {result.lessons_created}. "
            f"Цикл: {result.cycle}"
        ))

    # -------------------------------------------------------------- missing

    def _collect_missing(self, refs: DiscoveredReferences) -> list[tuple[str, str]]:
        missing: list[tuple[str, str]] = []

        if refs.funding_type and not FundingType.objects.filter(
            name=refs.funding_type
        ).exists():
            missing.append(("вид финансирования", refs.funding_type))

        if refs.base and not Base.objects.filter(name=refs.base).exists():
            missing.append(("база", refs.base))

        if refs.cycle_name and not CycleName.objects.filter(
            name=refs.cycle_name
        ).exists():
            missing.append(("название цикла", refs.cycle_name))

        for code in sorted(refs.lesson_types):
            if not LessonType.objects.filter(code=code).exists():
                missing.append(("тип занятия", code))

        for name in sorted(refs.employees):
            if not Employee.objects.filter(short_name=name).exists():
                missing.append(("сотрудник", name))

        return missing

    def _report_missing(self, missing: list[tuple[str, str]]) -> None:
        self.stdout.write(self.style.WARNING(
            "В файле упомянуты сущности, которых нет в БД:"
        ))
        for kind, name in missing:
            self.stdout.write(f"  • {kind}: {name!r}")
        self.stdout.write("")

    def _create_all(self, missing: list[tuple[str, str]]) -> bool:
        """True — все созданы (или пользователь согласился). False — отмена."""
        for kind, name in missing:
            if not self._create_one(kind, name):
                return False
        return True

    def _create_one(self, kind: str, name: str) -> bool:
        if not self._ask_yes_no(f"Добавить {kind} {name!r}? [y/N] "):
            self.stderr.write(f"Отказано: {kind} {name!r}")
            return False

        if kind == "вид финансирования":
            FundingType.objects.create(name=name)
        elif kind == "база":
            Base.objects.create(name=name)
        elif kind == "название цикла":
            CycleName.objects.create(name=name)
        elif kind == "тип занятия":
            return self._create_lesson_type(name)
        elif kind == "сотрудник":
            return self._create_employee(name)
        else:
            raise ValueError(f"unknown kind: {kind!r}")

        self.stdout.write(self.style.SUCCESS(f"Создано: {kind} {name!r}"))
        return True

    # --------------------------------------------------------- per-entity

    def _create_employee(self, short_name: str) -> bool:
        position = self._choose_position(short_name)
        if position is None:
            return False
        Employee.objects.create(short_name=short_name, position=position)
        self.stdout.write(self.style.SUCCESS(f"Создан сотрудник: {short_name}"))
        return True

    def _create_lesson_type(self, code: str) -> bool:
        name = self._ask("  Название: ").strip()
        if not name:
            self.stderr.write("  Название не может быть пустым.")
            return False

        last = (
            LessonType.objects
            .order_by("-sort_order")
            .values_list("sort_order", flat=True)
            .first()
        )
        default_order = (last or 0) + 10

        raw = self._ask(f"  Порядок сортировки [{default_order}]: ").strip()
        try:
            sort_order = int(raw) if raw else default_order
        except ValueError:
            self.stderr.write("  Порядок сортировки должен быть числом.")
            return False

        category = self._choose_category()

        counts = self._ask_yes_no(
            "  Учитывать в подсчёте часов? [Y/n] ", default=True,
        )

        LessonType.objects.create(
            code=code,
            name=name,
            sort_order=sort_order,
            category=category,
            counts_in_hours=counts,
        )
        self.stdout.write(self.style.SUCCESS(
            f"Создан тип занятия: {code} — {name}"
        ))
        return True

    def _choose_position(self, short_name: str) -> Position | None:
        positions = list(Position.objects.order_by("sort_order", "name"))
        if not positions:
            self.stderr.write(
                "  В БД нет ни одной должности. "
                "Создайте должность в админке и повторите."
            )
            return None

        self.stdout.write(f"  Должность для {short_name}:")
        for i, p in enumerate(positions, 1):
            self.stdout.write(
                f"    {i}. {p.name} (лимит {p.max_hours_per_day} ч/день)"
            )

        while True:
            raw = self._ask(f"  Номер [1-{len(positions)}, Enter = отмена]: ").strip()
            if not raw:
                return None
            try:
                idx = int(raw)
            except ValueError:
                self.stderr.write("  Введите число.")
                continue
            if 1 <= idx <= len(positions):
                return positions[idx - 1]
            self.stderr.write(f"  Введите число от 1 до {len(positions)}.")

    def _choose_category(self) -> str:
        options = list(LessonType.Category.choices)
        self.stdout.write("  Категория в отчёте:")
        for i, (_value, label) in enumerate(options, 1):
            self.stdout.write(f"    {i}. {label}")
        self.stdout.write(f"    {len(options) + 1}. (без категории)")

        while True:
            raw = self._ask(
                f"  Номер [1-{len(options) + 1}, Enter = без категории]: "
            ).strip()
            if not raw:
                return ""
            try:
                idx = int(raw)
            except ValueError:
                self.stderr.write("  Введите число.")
                continue
            if 1 <= idx <= len(options):
                return options[idx - 1][0]
            if idx == len(options) + 1:
                return ""
            self.stderr.write(f"  Введите число от 1 до {len(options) + 1}.")

    # ------------------------------------------------------------- input

    def _ask(self, prompt: str) -> str:
        return input(prompt)

    def _ask_yes_no(self, prompt: str, default: bool = False) -> bool:
        raw = input(prompt).strip().lower()
        if not raw:
            return default
        return raw in ("y", "yes", "д", "да")

