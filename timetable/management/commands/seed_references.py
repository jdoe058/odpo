from collections import OrderedDict

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from timetable.models import (
    FundingType, LessonType, Position, normalize_name,
)
from timetable.reference_data import (
    FUNDING_TYPES, LESSON_TYPES, POSITIONS,
)


GROUPS = ("funding", "positions", "lesson_types", "templates")


class Command(BaseCommand):
    help = (
        "Заполнить справочники каноническими данными: виды финансирования, "
        "должности, типы занятий; загрузить эталонные шаблоны документов. "
        "Существующие записи не изменяются — команда идемпотентна."
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
            "Заполнение справочников" + (" (dry-run)" if dry_run else "")
        ))

        stats = OrderedDict(
            (g, {"created": [], "existing": []}) for g in groups
        )

        with transaction.atomic():
            if "funding" in groups:
                self._seed_funding(stats["funding"])
            if "positions" in groups:
                self._seed_positions(stats["positions"])
            if "lesson_types" in groups:
                self._seed_lesson_types(stats["lesson_types"])

            if dry_run:
                transaction.set_rollback(True)

        if "templates" in groups:
            self._seed_templates(stats["templates"])

        self._print_summary(stats, dry_run)

    # ---------------------------------------------------------- seeders

    def _seed_templates(self, stat):
        self.stdout.write("\nШаблоны документов:")
        from timetable.exports.library import seed_templates
        for code, created in seed_templates():
            self._record(stat, code, created)

    def _seed_funding(self, stat):
        self.stdout.write("\nВиды финансирования:")
        for raw_name in FUNDING_TYPES:
            name = normalize_name(raw_name)
            obj, created = FundingType.objects.get_or_create(name=name)
            self._record(stat, obj.name, created)

    def _seed_positions(self, stat):
        self.stdout.write("\nДолжности:")
        for spec in POSITIONS:
            obj, created = Position.objects.get_or_create(
                name=spec.name,
                defaults={
                    "max_hours_per_day": spec.max_hours_per_day,
                    "can_sign": spec.can_sign,
                    "can_approve": spec.can_approve,
                    "sort_order": spec.sort_order,
                },
            )
            self._record(stat, obj.name, created)

    def _seed_lesson_types(self, stat):
        self.stdout.write("\nТипы занятий:")
        for spec in LESSON_TYPES:
            obj, created = LessonType.objects.get_or_create(
                code=spec.code,
                defaults={
                    "name": spec.name,
                    "category": spec.category,
                    "counts_in_hours": spec.counts_in_hours,
                    "sort_order": spec.sort_order,
                },
            )
            self._record(stat, f"{obj.code} — {obj.name}", created)

    # -------------------------------------------------------------- helpers

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

