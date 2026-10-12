"""Резервное копирование SQLite-базы."""
import sqlite3
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


DEFAULT_KEEP = 10


class Command(BaseCommand):
    help = "Создаёт резервную копию SQLite-базы в каталоге backups/."

    def add_arguments(self, parser):
        parser.add_argument(
            "--keep",
            type=int,
            default=DEFAULT_KEEP,
            help=(
                f"Сколько последних копий оставить. "
                f"0 — хранить все. По умолчанию {DEFAULT_KEEP}."
            ),
        )
        parser.add_argument(
            "--dir",
            type=str,
            default="",
            help="Каталог для копий. По умолчанию BASE_DIR/backups.",
        )

    def handle(self, *args, **options):
        db = settings.DATABASES.get("default", {})
        engine = db.get("ENGINE", "")

        if "sqlite3" not in engine:
            raise CommandError(
                "Команда поддерживает только SQLite. "
                "Для PostgreSQL используйте pg_dump."
            )

        source_path = Path(db["NAME"])
        if not source_path.exists():
            raise CommandError(f"Файл базы не найден: {source_path}")

        backup_dir = (
            Path(options["dir"]) if options["dir"]
            else settings.BASE_DIR / "backups"
        )
        backup_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        target_path = backup_dir / f"db_{timestamp}.sqlite3"

        # Безопасное копирование даже на «живой» базе.
        # sqlite3.Connection.backup() делает консистентный снимок.
        src = sqlite3.connect(str(source_path))
        try:
            dst = sqlite3.connect(str(target_path))
            try:
                src.backup(dst)
            finally:
                dst.close()
        finally:
            src.close()

        size_kb = target_path.stat().st_size // 1024
        self.stdout.write(self.style.SUCCESS(
            f"Создан бэкап: {target_path} ({size_kb} КБ)"
        ))

        keep = options["keep"]
        if keep > 0:
            removed = self._cleanup(backup_dir, keep)
            for path in removed:
                self.stdout.write(f"Удалён старый бэкап: {path.name}")

    def _cleanup(self, backup_dir: Path, keep: int) -> list[Path]:
        """Удаляет старые копии, оставляя последние `keep`."""
        files = sorted(
            backup_dir.glob("db_*.sqlite3"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        removed: list[Path] = []
        for path in files[keep:]:
            path.unlink()
            removed.append(path)
        return removed
    