from collections.abc import Iterable
from enum import Enum


class FeedbackFormModuleType(str, Enum):
    MARKDOWN = ("markdown", "Markdown", "markdownfeedbackmodule")
    SCORE_TABLE = ("score_table", "Score Table", "scoretablefeedbackmodule")
    CHOICE_RESPONSE_LIST = (
        "choice_response_list",
        "Choice Response List",
        "choiceresponselistfeedbackmodule",
    )
    FREE_TEXT_LIST = ("free_text_list", "Free Text List", "freetextlistfeedbackmodule")

    def __new__(cls, value, label, child_attribute) -> "FeedbackFormModuleType":
        obj = str.__new__(cls, value)
        obj._value_ = value
        obj.label = label
        obj.child_attribute = child_attribute
        return obj

    @classmethod
    def choices(cls) -> Iterable[tuple[str, str]]:
        return [(item.value, item.label) for item in cls]
