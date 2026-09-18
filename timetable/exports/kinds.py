from dataclasses import dataclass
from typing import Any, Callable

from timetable.services.approvers import find_approver


# ---------------------------------------------------------------------
# Контракт шаблона
# ---------------------------------------------------------------------
# Любой .docx-шаблон может рассчитывать на следующие переменные:
#   cycle_name, funding, base, start, end
#   signer, signer_position
#   approver, approver_position
# Плюс всё, что положит в контекст конкретная спецификация.
# ---------------------------------------------------------------------


def build_common_context(cycle) -> dict:
    """Поля, общие для всех выгрузок."""
    signer = cycle.compiled_by
    approver = find_approver()

    return {
        "cycle_name": cycle.name.name,
        "funding": cycle.funding_type.name if cycle.funding_type else "",
        "base": cycle.base.name,
        "start": cycle.start_date.strftime("%d.%m.%Y"),
        "end": cycle.end_date.strftime("%d.%m.%Y"),
        "signer": signer.short_name if signer else "",
        "signer_position": signer.position.name if signer and signer.position else "",
        "approver": approver.short_name if approver else "",
        "approver_position": (
            approver.position.name if approver and approver.position else ""
        ),
    }


@dataclass(frozen=True)
class ExporterSpec:
    code: str
    name: str
    sort_order: int
    build_own_context: Callable[[Any], dict]   # только специфичные поля
    build_filename: Callable[[Any], str]

    def build_context(self, cycle) -> dict:
        return {**build_common_context(cycle), **self.build_own_context(cycle)}


_REGISTRY: dict[str, ExporterSpec] = {}


def register(spec: ExporterSpec) -> ExporterSpec:
    if spec.code in _REGISTRY:
        raise ValueError(
            f"Exporter already registered: {spec.code!r}. "
            f"Known: {', '.join(sorted(_REGISTRY))}"
        )
    _REGISTRY[spec.code] = spec
    return spec


def get(code: str) -> ExporterSpec:
    try:
        return _REGISTRY[code]
    except KeyError:
        raise KeyError(
            f"Unknown exporter: {code!r}. "
            f"Known: {', '.join(sorted(_REGISTRY))}"
        )


def all_specs() -> list[ExporterSpec]:
    return sorted(_REGISTRY.values(), key=lambda s: (s.sort_order, s.name))


def codes() -> list[str]:
    return [s.code for s in all_specs()]