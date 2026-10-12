"""CBV и view для работы с занятиями."""
from .actions import lesson_cell_update, lesson_recalculate_breaks
from .create import LessonCreate
from .delete import LessonDelete
from .edit import LessonEdit
from .list import LessonList

__all__ = [
    "LessonList",
    "LessonCreate",
    "LessonEdit",
    "LessonDelete",
    "lesson_cell_update",
    "lesson_recalculate_breaks",
]