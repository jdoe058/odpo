import re
from collections import defaultdict


_LINE_RE = re.compile(r"^Строка (\d+): (.*)$")


class ScheduleImportError(Exception):
    """Ошибки импорта — список человекочитаемых сообщений."""
    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__("; ".join(errors))


def compress_ranges(numbers: list[int]) -> str:
    """[9,10,11,12,17] → 'строки 9–12, 17'."""
    numbers = sorted(set(numbers))
    if not numbers:
        return ""
    ranges = []
    start = prev = numbers[0]
    for n in numbers[1:]:
        if n == prev + 1:
            prev = n
            continue
        ranges.append((start, prev))
        start = prev = n
    ranges.append((start, prev))

    parts = [str(a) if a == b else f"{a}–{b}" for a, b in ranges]
    return "строки " + ", ".join(parts)


def group_errors(errors: list[str]) -> list[str]:
    """'Строка 9: X' + 'Строка 10: X' → 'X — строки 9, 10'."""
    grouped: dict[str, list[int]] = defaultdict(list)
    ungrouped: list[str] = []

    for err in errors:
        m = _LINE_RE.match(err)
        if m:
            grouped[m.group(2)].append(int(m.group(1)))
        else:
            ungrouped.append(err)

    result = [
        f"{msg} — {compress_ranges(sorted(set(rows)))}"
        for msg, rows in grouped.items()
    ]
    result.extend(ungrouped)
    return result

