"""CBV для справочников + view обмена."""
from .create import ReferenceCreate
from .delete import ReferenceDelete
from .edit import ReferenceEdit
from .exchange import exchange_view, export_view
from .list import ReferenceList

__all__ = [
    "ReferenceList",
    "ReferenceCreate",
    "ReferenceEdit",
    "ReferenceDelete",
    "exchange_view",
    "export_view",
]