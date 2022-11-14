from typing import Any, Optional

import mistletoe
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.forms import model_to_dict

from apps.rubrics.constants import FeedbackFormModuleType
from apps.rubrics.models.base import ValidatedModel


class MarkdownField(models.TextField):
    def __init__(self, **kwargs) -> None:
        validators = kwargs.get("validators", [])
        if MarkdownField.validate_markdown not in validators:
            validators.append(MarkdownField.validate_markdown)
        kwargs["validators"] = validators

        super().__init__(**kwargs)

    @staticmethod
    def validate_markdown(value):
        try:
            mistletoe.markdown(value)
        except Exception as err:
            raise ValidationError(err)

    def value_to_html(self, obj: models.Model) -> str:
        value = self.value_from_object(obj)
        return mistletoe.markdown(value)


class FeedbackForm(models.Model):
    rubric = models.ForeignKey("Rubric", on_delete=models.CASCADE)

    def __str__(self):
        return f"Feedback Form for {self.rubric.name}"


class FeedbackModule(ValidatedModel):
    MODULE_TYPE = None

    feedback_form = models.ForeignKey(
        "FeedbackForm", on_delete=models.CASCADE, related_name="modules"
    )
    order = models.PositiveIntegerField(null=False, blank=False)
    module_type = models.CharField(
        max_length=50,
        choices=FeedbackFormModuleType.choices(),
        null=False,
        blank=False,
    )

    class Meta:
        ordering = ("order", "pk")

    @classmethod
    def validate(cls, **fields):
        if not fields.get("module_type", None):
            raise ValidationError("Must specify a value for module_type")
        if not fields.get("order", None):
            raise ValidationError("Must specify a value for order")

    @transaction.atomic()
    def save(self, **kwargs):
        # Do this inside a transaction. If creating the child item fails,
        # the parent object should be rolled back
        is_new_object = self._state.adding
        super().save(**kwargs)

        if is_new_object and type(self) == FeedbackModule:
            self._save_child_object()

    def _save_child_object(self) -> Optional["FeedbackModule"]:
        for subclass in type(self).__subclasses__():
            if subclass.MODULE_TYPE == self.module_type:
                return subclass.objects.create(**self._to_child_field_dict())
        raise ValidationError(f"No child model created for {self}")

    def _to_child_field_dict(self) -> dict[str, Any]:
        return {
            "base_module": self,
            "feedback_form_id": self.feedback_form_id,
            "module_type": self.module_type,
            "order": self.order,
        }


class MarkdownFeedbackModule(FeedbackModule):
    MODULE_TYPE = FeedbackFormModuleType.MARKDOWN

    base_module = models.OneToOneField(
        "FeedbackModule", on_delete=models.CASCADE, parent_link=True, primary_key=True
    )
    content = MarkdownField(default="# Heading 1\n\nWrite content here")

    def get_html(self):
        return self._meta.get_field("content").value_to_html(self)

    def __str__(self):
        l = min(50, self.content.find("\n"))
        first_line = self.content[:l]
        return f"Markdown module ({self.order}) - {first_line}"
