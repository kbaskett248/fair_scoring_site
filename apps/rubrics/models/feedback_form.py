from typing import Any, Generator, NamedTuple, Optional

import mistletoe
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import QuerySet
from django.template.loader import render_to_string
from django.utils.safestring import SafeString, mark_safe

from apps.rubrics.constants import FeedbackFormModuleType
from apps.rubrics.models.base import ValidatedModel
from apps.rubrics.models.rubric import RubricResponse


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
    TEMPLATE = "rubrics/feedback_form.html"

    class FeedbackFormContext(NamedTuple):
        form: "FeedbackForm"
        html: SafeString

    rubric = models.ForeignKey("Rubric", on_delete=models.CASCADE)

    def __str__(self):
        return f"Feedback Form for {self.rubric.name}"

    def get_typed_modules(self) -> Generator["FeedbackModule", None, None]:
        for module in self.modules.all():
            yield module.get_typed_module()

    def get_template(self) -> str:
        return self.TEMPLATE

    def get_context(
        self, rubric_responses: models.QuerySet[RubricResponse]
    ) -> dict[str, Any]:
        return {
            "modules": [
                module.render_html(rubric_responses)
                for module in self.get_typed_modules()
            ]
        }

    def render_html(
        self, rubric_responses: models.QuerySet[RubricResponse]
    ) -> SafeString:
        rubric_responses = rubric_responses.filter(rubric=self.rubric)
        return mark_safe(
            render_to_string(self.get_template(), self.get_context(rubric_responses))
        )

    class FeedbackFormManager(models.Manager):
        def get_queryset(self) -> QuerySet["FeedbackForm"]:
            return (
                super()
                .get_queryset()
                .select_related("rubric")
                .prefetch_related("modules")
            )

        def for_rubric_responses(
            self, rubric_responses: QuerySet[RubricResponse]
        ) -> QuerySet["FeedbackForm"]:
            """
            Args:
                rubric_responses (QuerySet[RubricResponse]): a queryset of rubric responses

            Returns:
                QuerySet[RubricResponse]: a queryset of FeedbackForms for the
                    given queryset of RubricResponses
            """
            rubric_set = set(rubric_responses.values_list("rubric__id", flat=True))
            return self.get_queryset().filter(rubric__in=rubric_set)

        def render_html_for_responses(
            self, rubric_responses: QuerySet[RubricResponse]
        ) -> Generator["FeedbackForm.FeedbackFormContext", None, None]:
            """Render html for each feedback form associated with the rubric responses."""
            for feedback_form in self.for_rubric_responses(rubric_responses):
                yield FeedbackForm.FeedbackFormContext(
                    feedback_form, feedback_form.render_html(rubric_responses)
                )

    objects = FeedbackFormManager()


class FeedbackModule(ValidatedModel):
    MODULE_TYPE = None
    TEMPLATE = ""

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

    def get_typed_module(self) -> "FeedbackModule":
        if self.module_type == FeedbackFormModuleType.MARKDOWN:
            return self.markdownfeedbackmodule
        return self

    def get_template(self) -> str:
        return self.TEMPLATE

    def get_context(
        self, rubric_responses: models.QuerySet[RubricResponse]
    ) -> dict[str, Any]:
        raise NotImplementedError

    def render_html(
        self, rubric_responses: models.QuerySet[RubricResponse]
    ) -> SafeString:
        return mark_safe(
            render_to_string(self.get_template(), self.get_context(rubric_responses))
        )


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

    def render_html(self, rubric_responses: models.QuerySet[RubricResponse]):
        return mark_safe(self.get_html())
