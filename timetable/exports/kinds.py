from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class ExporterSpec:
    """
    Описание одной выгрузки. Живёт в Python, не в БД:
    build_context / build_filename — обычные функции, которые
    нельзя хранить в таблице без потери типобезопасности.
    """
    code: str
    name: str
    sort_order: int
    build_context: Callable[[Any], dict]
    build_filename: Callable[[Any], str]


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