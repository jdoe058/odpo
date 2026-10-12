"""Логика inline-редактирования ячеек справочников."""


def get_inline_value(obj, col):
    """Значение поля для отображения в ячейке."""
    value = getattr(obj, col.name, "")

    if col.kind == "bool":
        return bool(value)

    if col.kind == "fk_name" and value is not None:
        return str(value)

    if value is None:
        return ""

    return value