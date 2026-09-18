from collections import OrderedDict
from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from timetable.demo_data import (
    BASES, CYCLES, CYCLE_NAMES, EMPLOYEES,
)
from timetable.models import (
    Base, Cycle, CycleName, Employee, FundingType, Lesson, LessonType,
    Position, normalize_name, normalize_short_name,
)


GROUPS = ("bases", "employees", "cycle_names", "cycles")


class Command(BaseCommand):
    help = (
        "Загрузить демонстрационные данные: базы, сотрудников, названия "
        "циклов, циклы и занятия. Существующие записи не изменяются — "
        "команда идемпотентна. Требует предварительно выполненного "
        "seed_references."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--only",
            default=",".join(GROUPS),
            help=(
                "Какие группы заполнять, через запятую. "
                f"Доступные: {', '.join(GROUPS)}. По умолчанию — все."
            ),
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Показать, что было бы создано, но ничего не писать в БД.",
        )

    # -------------------------------------------------------------- handle

    def handle(self, *args, **opts):
        groups = self._parse_groups(opts["only"])
        dry_run = opts["dry_run"]

        self.stdout.write(self.style.MIGRATE_HEADING(
            "Загрузка демо-данных" + (" (dry-run)" if dry_run else "")
        ))

        stats = OrderedDict(
            (g, {"created": [], "existing": []}) for g in groups
        )

        with transaction.atomic():
            if "bases" in groups:
                self._seed_bases(stats["bases"])
            if "employees" in groups:
                self._seed_employees(stats["employees"])
            if "cycle_names" in groups:
                self._seed_cycle_names(stats["cycle_names"])
            if "cycles" in groups:
                self._seed_cycles(stats["cycles"])

            if dry_run:
                transaction.set_rollback(True)

        self._print_summary(stats, dry_run)

    # ----------------------------------------------------------- seeders

    def _seed_bases(self, stat):
        self.stdout.write("\nБазы:")
        for spec in BASES:
            obj, created = Base.objects.get_or_create(name=spec.name)
            self._record(stat, obj.name, created)

    def _seed_employees(self, stat):
        self.stdout.write("\nСотрудники:")
        for spec in EMPLOYEES:
            try:
                position = Position.objects.get(name=spec.position)
            except Position.DoesNotExist:
                raise CommandError(
                    f"Должность {spec.position!r} не найдена. "
                    "Сначала выполните: "
                    "python manage.py seed_references --only positions"
                )
            short_name = normalize_short_name(spec.short_name)
            obj, created = Employee.objects.get_or_create(
                short_name=short_name,
                defaults={"position": position},
            )
            self._record(stat, f"{obj.short_name} ({position.name})", created)

    def _seed_cycle_names(self, stat):
        self.stdout.write("\nНазвания циклов:")
        for spec in CYCLE_NAMES:
            obj, created = CycleName.objects.get_or_create(name=spec.name)
            self._record(stat, obj.name, created)

    def _seed_cycles(self, stat):
        self.stdout.write("\nЦиклы:")
        for spec in CYCLES:
            name = self._get(CycleName, name=spec.name)
            base = self._get(Base, name=spec.base)
            funding = self._get(
                FundingType, name=normalize_name(spec.funding),
            )
            compiled_by = self._get(
                Employee, short_name=normalize_short_name(spec.compiled_by),
            )

            cycle, created = Cycle.objects.get_or_create(
                name=name, base=base, start_date=spec.start_date,
                defaults={
                    "funding_type": funding,
                    "end_date": spec.end_date,
                    "compiled_by": compiled_by,
                    "in_archive": False,
                },
            )
            self._record(stat, str(cycle), created)

            # Занятия создаём только для новых циклов: у Lesson нет
            # естественного уникального ключа, повторный запуск на
            # существующем цикле продублировал бы строки.
            if created:
                self._seed_lessons(cycle, spec.lessons)

    def _seed_lessons(self, cycle, lesson_specs):
        for lspec in lesson_specs:
            lesson_type = self._get(LessonType, code=lspec.lesson_type_code)
            employee = self._get(
                Employee, short_name=normalize_short_name(lspec.employee),
            )
            Lesson.objects.create(
                cycle=cycle,
                date=cycle.start_date + timedelta(days=lspec.day),
                time_start=lspec.time_start,
                hours=lspec.hours,
                lesson_type=lesson_type,
                topic=lspec.topic,
                employee=employee,
            )

    # ------------------------------------------------------------ helpers

    def _get(self, model, **kwargs):
        try:
            return model.objects.get(**kwargs)
        except model.DoesNotExist:
            raise CommandError(
                f"{model.__name__} не найден по {kwargs!r}. "
                "Выполните: python manage.py seed_references"
            )

    def _record(self, stat, label: str, created: bool) -> None:
        if created:
            stat["created"].append(label)
            self.stdout.write(f"  {self.style.SUCCESS('+')} {label}")
        else:
            stat["existing"].append(label)
            self.stdout.write(f"  = {label}")

    def _parse_groups(self, raw: str) -> list[str]:
        if not raw.strip():
            raise CommandError("--only не может быть пустым.")
        groups = [g.strip() for g in raw.split(",") if g.strip()]
        unknown = [g for g in groups if g not in GROUPS]
        if unknown:
            raise CommandError(
                f"Неизвестные группы: {', '.join(unknown)}. "
                f"Доступные: {', '.join(GROUPS)}."
            )
        return groups

    def _print_summary(self, stats, dry_run: bool) -> None:
        self.stdout.write("")
        self.stdout.write(self.style.MIGRATE_HEADING("Итог"))
        total_created = total_existing = 0
        for group, stat in stats.items():
            c, e = len(stat["created"]), len(stat["existing"])
            total_created += c
            total_existing += e
            self.stdout.write(f"  {group}: создано {c}, уже было {e}")
        self.stdout.write(
            f"  всего: создано {total_created}, уже было {total_existing}"
        )
        if dry_run:
            self.stdout.write(self.style.WARNING(
                "Dry-run: изменения в БД не применены."
            ))
        else:
            self.stdout.write(self.style.SUCCESS("Готово."))