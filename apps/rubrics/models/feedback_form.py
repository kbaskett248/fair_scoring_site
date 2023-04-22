from itertools import groupby
from typing import Any, Generator, Iterable, NamedTuple, Optional

import mistletoe
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import QuerySet
from django.template.loader import render_to_string
from django.utils.safestring import SafeString, mark_safe

from apps.rubrics.constants import FeedbackFormModuleType
from apps.rubrics.models.base import ValidatedModel
from apps.rubrics.models.rubric import Question, QuestionResponse, RubricResponse


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
        try:
            module_type = FeedbackFormModuleType(self.module_type)
        except ValueError:
            return self
        else:
            return getattr(self, module_type.child_attribute)

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
    content = MarkdownField(
        default="# Heading 1\n\nWrite content here",
        help_text="You may include <code>{{ average_score }}</code> in the text. It will be replaced by the average score for the project.",
    )

    def get_html(self):
        return self._meta.get_field("content").value_to_html(self)

    def __str__(self):
        l = min(50, self.content.find("\n"))
        first_line = self.content[:l]
        return f"Markdown module ({self.order}) - {first_line}"

    def render_html(self, rubric_responses: models.QuerySet[RubricResponse]):
        return mark_safe(
            self.get_html().replace(
                "{{ average_score }}", f'{self._get_average_score(rubric_responses):.2f}'
            )
        )

    def _get_average_score(
        self, rubric_responses: models.QuerySet[RubricResponse]
    ) -> float | None:
        responses = [
            response.score() for response in rubric_responses if response.has_response
        ]
        if not responses:
            return None
        return sum(responses) / len(responses)


class ScoreTableFeedbackModule(FeedbackModule):
    MODULE_TYPE = FeedbackFormModuleType.SCORE_TABLE
    TEMPLATE = "rubrics/modules/score_table_module.html"

    class QuestionRow(NamedTuple):
        short_description: str
        long_description: str
        score: float | None

    base_module = models.OneToOneField(
        "FeedbackModule", on_delete=models.CASCADE, parent_link=True, primary_key=True
    )
    questions = models.ManyToManyField(
        "Question", limit_choices_to={"question_type__in": Question.CHOICE_TYPES}
    )

    include_short_description = models.BooleanField(default=True)
    include_long_description = models.BooleanField(default=True)

    table_title = models.CharField("Table title", max_length=200, blank=True)
    short_description_title = models.CharField(
        "Short description title", max_length=50, blank=True
    )
    long_description_title = models.CharField(
        "Long description title", max_length=50, blank=True
    )
    score_title = models.CharField("Score title", max_length=50, blank=True)

    use_weighted_scores = models.BooleanField("Use weighted scores", default=False)
    remove_empty_scores = models.BooleanField("Remove empty scores", default=True)

    def __str__(self) -> str:
        result = f"Score table module ({self.order})"
        if self.table_title:
            result += f" - {self.table_title}"
        return result

    def get_context(
        self, rubric_responses: models.QuerySet[RubricResponse]
    ) -> dict[str, Any]:
        return {
            "include_header": (
                self.short_description_title
                or self.long_description_title
                or self.score_title
            ),
            "module": self,
            "rows": self.get_rows(rubric_responses),
        }

    def get_rows(
        self, rubric_responses: models.QuerySet[RubricResponse]
    ) -> Generator[QuestionRow, None, None]:
        question_qs = (
            QuestionResponse.objects.filter(
                rubric_response__in=rubric_responses, question__in=self.questions.all()
            )
            .select_related("question", "rubric_response")
            .order_by("question__order", "question")
        )
        question_responses = filter(
            lambda q: q.rubric_response.has_response, question_qs
        )
        question_groups = (
            list(responses)
            for _, responses in groupby(question_responses, lambda q: q.question_id)
        )
        for group in question_groups:
            yield self.build_row(group)

    def build_row(self, question_responses: list[QuestionResponse]) -> QuestionRow:
        question = question_responses[0].question
        short_description = question.short_description
        long_description = question.long_description

        if self.use_weighted_scores:
            get_score = lambda resp: resp.score()
        else:
            get_score = lambda resp: resp.unweighted_score()
        scores = map(get_score, question_responses)

        if self.remove_empty_scores:
            scores = filter(None, scores)

        return self.QuestionRow(
            short_description, long_description, self._average(list(scores))
        )

    def _average(self, scores: list[float]) -> float | None:
        try:
            return sum(scores) / len(scores)
        except TypeError:
            return None


class ChoiceResponseListFeedbackModule(FeedbackModule):
    MODULE_TYPE = FeedbackFormModuleType.CHOICE_RESPONSE_LIST
    TEMPLATE = "rubrics/modules/choice_response_list_module.html"

    base_module = models.OneToOneField(
        "FeedbackModule", on_delete=models.CASCADE, parent_link=True, primary_key=True
    )
    question = models.ForeignKey(
        "Question",
        on_delete=models.CASCADE,
        null=True,
        limit_choices_to={"question_type__in": Question.CHOICE_TYPES},
    )

    display_description = models.BooleanField(
        "Display description",
        default=True,
        help_text="If checked, the choice description is displayed in the list. Otherwise the choice key is displayed.",
    )

    remove_duplicates = models.BooleanField(
        "Remove duplicates",
        default=True,
        help_text=(
            "If checked, response choices will only be displayed once, regardless of how many times the response is chosen. "
            "Otherwise, choices will be listed once for each time they are chosen."
        ),
    )

    def __str__(self) -> str:
        result = f"Choice response list module ({self.order})"
        if self.question:
            result += f": {self.question}"
        return result

    def get_context(
        self, rubric_responses: models.QuerySet[RubricResponse]
    ) -> dict[str, Any]:
        return {"responses": self._get_response_list(rubric_responses)}

    def _get_response_list(
        self, rubric_responses: models.QuerySet[RubricResponse]
    ) -> list[str]:
        if not self.question:
            return []

        question_qs = QuestionResponse.objects.filter(
            rubric_response__in=rubric_responses, question=self.question_id
        ).select_related("question", "rubric_response")
        question_responses = filter(
            lambda q: q.rubric_response.has_response, question_qs
        )

        responses = list(self._expand_responses(question_responses))

        if self.remove_duplicates:
            responses = dict(responses).items()

        if self.display_description:
            return [resp[1] for resp in responses]
        else:
            return [resp[0] for resp in responses]

    def _expand_responses(
        self, question_responses: Iterable[QuestionResponse]
    ) -> Generator[tuple[str, str], None, None]:
        for resp in question_responses:
            if not resp:
                continue
            elif isinstance(resp.response, list) and isinstance(
                resp.response_external(), list
            ):
                yield from zip(resp.response, resp.response_external())
            else:
                yield (resp.response, resp.response_external())


class FreeTextListFeedbackModule(FeedbackModule):
    MODULE_TYPE = FeedbackFormModuleType.FREE_TEXT_LIST
    TEMPLATE = "rubrics/modules/free_text_list_module.html"

    base_module = models.OneToOneField(
        "FeedbackModule", on_delete=models.CASCADE, parent_link=True, primary_key=True
    )
    question = models.ForeignKey(
        "Question",
        on_delete=models.CASCADE,
        null=True,
        limit_choices_to={"question_type": Question.LONG_TEXT},
    )

    def __str__(self) -> str:
        result = f"Free text list module ({self.order})"
        if self.question:
            result += f": {self.question}"
        return result

    def get_context(
        self, rubric_responses: models.QuerySet[RubricResponse]
    ) -> dict[str, Any]:
        return {"responses": self._get_response_list(rubric_responses)}

    def _get_response_list(
        self, rubric_responses: models.QuerySet[RubricResponse]
    ) -> list[str]:
        if not self.question:
            return []

        question_qs = QuestionResponse.objects.filter(
            rubric_response__in=rubric_responses, question=self.question_id
        ).select_related("question", "rubric_response")
        question_responses = filter(
            lambda q: q.rubric_response.has_response, question_qs
        )

        return list(
            filter(None, (resp.response_external() for resp in question_responses))
        )
