from io import BytesIO
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from timetable.models import (
    Base, CycleName, Employee, Position,
)
from timetable.imports import ScheduleImportError, import_schedule
from timetable.imports.discovery import DiscoveredReferences, discover_references


class Command(BaseCommand):
    help = (
        "Загрузить расписание из XLSX. Если в файле упомянуты сущности, "
        "которых нет в БД, команда спрашивает, добавлять ли их "
        "(кроме видов финансирования, типов занятий и должностей)."
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

        if refs.base and not Base.objects.filter(name=refs.base).exists():
            missing.append(("база", refs.base))

        if refs.cycle_name and not CycleName.objects.filter(
            name=refs.cycle_name
        ).exists():
            missing.append(("название цикла", refs.cycle_name))

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
        if not self._ask_yes_no(f"Добавить {kind} {name!r}? [Y/n] "):
            self.stderr.write(f"Отказано: {kind} {name!r}")
            return False

        if kind == "база":
            Base.objects.create(name=name)
        elif kind == "название цикла":
            CycleName.objects.create(name=name)
        elif kind == "сотрудник":
            return self._create_employee(name)
        else:
            raise ValueError(f"unknown kind: {kind!r}")

        self.stdout.write(self.style.SUCCESS(f"Создано: {kind} {name!r}"))
        return True

    # --------------------------------------------------------- per-entity

    def _create_employee(self, short_name: str) -> bool:
        try:
            position = Position.objects.get(name="преподаватель-совместитель")
        except Position.DoesNotExist:
            self.stderr.write(
                "  В БД нет должности 'преподаватель-совместитель'. "
                "Создайте её в админке и повторите."
            )
            return False
        except Position.MultipleObjectsReturned:
            self.stderr.write(
                "  В БД несколько должностей 'преподаватель-совместитель'. "
                "Оставьте одну и повторите."
            )
            return False

        Employee.objects.create(short_name=short_name, position=position)
        self.stdout.write(self.style.SUCCESS(f"Создан сотрудник: {short_name}"))
        return True

    # ------------------------------------------------------------- input

    def _ask(self, prompt: str) -> str:
        return input(prompt)

    def _ask_yes_no(self, prompt: str, default: bool = True) -> bool:
        raw = input(prompt).strip().lower()
        if not raw:
            return default
        return raw in ("y", "yes", "д", "да")
