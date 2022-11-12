from enum import Enum
from typing import Any, Iterable, Tuple


class FeedbackFormModuleType(str, Enum):
    MARKDOWN = ("markdown", "Markdown")

    def __new__(cls, value, label):
        obj = str.__new__(cls, value)
        obj._value_ = value
        obj.label = label
        return obj

    @classmethod
    def choices(cls) -> Iterable[Tuple[Any, str]]:
        return [(item.value, item.label) for item in cls]
