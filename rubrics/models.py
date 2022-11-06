import json

from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import Max, Q
from django.utils import timezone


def value_is_numeric(value) -> bool:
    try:
        float(value)
    except ValueError:
        return False
    else:
        return True


class ValidatedModel(models.Model):
    """Adds additional validation to a model on save.

    This class defines a framework for adding additional validation
    on save of an object. The validation is written in such a way that it
    can easily be re-used by forms. As such, the validation functions expect
    dictionaries.
    """

    class Meta:
        abstract = True

    def save(self, **kwargs):
        data = self.get_field_dict()
        self.validate(**data)
        self.validate_instance(**data)

        super(ValidatedModel, self).save(**kwargs)

    def get_field_dict(self) -> dict:
        data = {}
        for field in self._meta.fields:
            data[field.name] = getattr(self, field.name)
        return data

    def validate_instance(self, **fields):
        pass

    @classmethod
    def validate(cls, **fields):
        pass


class Rubric(ValidatedModel):
    name = models.CharField(max_length=200)

    def __str__(self):
        return self.name

    @property
    def ordered_question_set(self):
        return self.question_set.order_by("order")

    @classmethod
    def validate(cls, **fields):
        super().validate(**fields)
        if not fields.get("name", None):
            raise ValidationError("name required for Rubric")


class Question(ValidatedModel):
    SCALE_TYPE = "SCALE"
    SINGLE_SELECT_TYPE = "SINGLE SELECT"
    MULTI_SELECT_TYPE = "MULTI SELECT"
    LONG_TEXT = "LONG TEXT"
    TYPES = (
        (SCALE_TYPE, "Scale"),
        (SINGLE_SELECT_TYPE, "Single Select"),
        (MULTI_SELECT_TYPE, "Multi-Select"),
        (LONG_TEXT, "Free Text (Long)"),
    )
    CHOICE_TYPES = (SCALE_TYPE, SINGLE_SELECT_TYPE, MULTI_SELECT_TYPE)

    AUTO_SORT = "A"
    MANUAL_SORT = "M"
    SORT_CHOICES = ((AUTO_SORT, "Auto"), (MANUAL_SORT, "Manual"))

    rubric = models.ForeignKey("Rubric", on_delete=models.CASCADE)
    order = models.PositiveSmallIntegerField(null=True, blank=True)
    short_description = models.CharField(max_length=200)
    long_description = models.TextField(null=True, blank=True)
    help_text = models.TextField(null=True, blank=True)
    weight = models.DecimalField(max_digits=4, decimal_places=3, null=True)
    question_type = models.CharField(max_length=20, choices=TYPES)
    choice_sort = models.CharField(max_length=1, choices=SORT_CHOICES)
    required = models.BooleanField(default=True)

    ordering = ("rubric", "order", "short_description")

    def __init__(self, *args, **kwargs):
        # __init__ is run when objects are retrieved from the database
        # in addition to when they are created.
        super(Question, self).__init__(*args, **kwargs)
        if not self.order:
            self.order = self._get_next_order()

        self.__original_question_type = self.question_type

    def _get_next_order(self):
        try:
            max_order = Question.objects.filter(rubric=self.rubric).aggregate(
                models.Max("order")
            )["order__max"]
        except Rubric.DoesNotExist:
            return

        if max_order:
            return max_order + 1
        else:
            return 1

    def __str__(self):
        return self.short_description

    def show_choices(self):
        return QuestionType.get_instance(self).show_choices()

    def num_choices_display(self):
        if self.show_choices():
            return self.choice_set.count()
        else:
            return "-"

    def description(self):
        return self.long_description or self.short_description

    def choices(self):
        for choice in self.choice_set.all():
            yield (choice.key, choice.description)

    def field_name(self):
        return "question_%s" % self.pk

    def add_choice(self, key, description, order=None):
        choice = Choice(question=self, key=key, description=description)
        if order:
            choice.order = order
        choice.save()
        return choice

    def question_type_changed(self) -> bool:
        return self.question_type != self.__original_question_type

    def question_type_changed_compatibility(self) -> bool:
        compatible_types = [Question.SCALE_TYPE, Question.SINGLE_SELECT_TYPE]
        if (self.question_type in compatible_types) and (
            self.__original_question_type in compatible_types
        ):
            return False
        else:
            return self.question_type_changed()

    def validate_instance(
        self,
        rubric=None,
        order=None,
        short_description=None,
        long_description=None,
        help_text=None,
        weight=None,
        question_type=None,
        choice_sort=None,
        required=None,
        **additional_fields
    ):
        if question_type in self.CHOICE_TYPES and weight and weight > 0:
            keys = [item["key"] for item in self.choice_set.values("key").all()]
            for key in keys:
                if not value_is_numeric(key):
                    raise ValidationError(
                        "The choice keys for a weighted question must be numeric. "
                        'The value "%(key)s" is non-numeric.',
                        code="non-numeric key",
                        params={"key": key},
                    )
                break

    @classmethod
    def validate(
        cls,
        rubric=None,
        order=None,
        short_description=None,
        long_description=None,
        help_text=None,
        weight=None,
        question_type=None,
        choice_sort=None,
        required=None,
        **additional_fields
    ):
        if not rubric:
            raise ValidationError("Rubric required for question", code="required")

        if not question_type:
            raise ValidationError(
                "Question_type required for question", code="required"
            )

        if not cls.is_allowed_type(question_type):
            raise ValidationError(
                "Question_type was %(question_type)s. Should be one of %(available_types)s.",
                code="invalid question type",
                params={
                    "question_type": question_type,
                    "available_types": cls.available_types(),
                },
            )

        if not cls.is_allowed_sort(choice_sort):
            raise ValidationError(
                "Choice_sort was %(choice_sort)s. Should be one of %(sort_options)s.",
                code="invalid choice sort",
                params={"choice_sort": choice_sort, "sort_options": cls.SORT_CHOICES},
            )

        if weight:
            if weight < 0:
                raise ValidationError(
                    "Weight must be a positive number",
                    code="negative weight not allowed",
                    params={"weight": weight},
                )
            elif weight > 0 and question_type not in cls.CHOICE_TYPES:
                raise ValidationError(
                    'Weight not allowed for questions of type "%(question_type)s"',
                    code="weight not allowed",
                    params={"question_type": question_type},
                )

    @classmethod
    def available_types(cls):
        return [typ[0] for typ in cls.TYPES]

    @classmethod
    def is_allowed_type(cls, question_type):
        return question_type in cls.available_types()

    @classmethod
    def sort_options(cls):
        return [srt[0] for srt in cls.SORT_CHOICES]

    @classmethod
    def is_allowed_sort(cls, sort_option):
        return sort_option in cls.sort_options()


class Choice(ValidatedModel):
    question = models.ForeignKey("Question", on_delete=models.CASCADE)
    order = models.PositiveSmallIntegerField(null=True, blank=True)
    key = models.CharField(max_length=20)
    description = models.CharField(max_length=200)

    ordering = ("question", "order", "key")

    def __init__(self, *args, **kwargs):
        # __init__ is run when objects are retrieved from the database
        # in addition to when they are created.
        super(Choice, self).__init__(*args, **kwargs)
        if not self.order:
            self.order = self._get_next_order()

    def _get_next_order(self):
        try:
            max_order = Choice.objects.filter(question=self.question).aggregate(
                models.Max("order")
            )["order__max"]
        except Question.DoesNotExist:
            return

        if max_order:
            return max_order + 1
        else:
            return 1

    def __str__(self):
        return self.description

    @classmethod
    def validate(
        cls, question=None, order=None, key=None, description=None, **additional_fields
    ):
        if not question:
            raise ValidationError("Question required for choice.", code="required")
        if not key:
            raise ValidationError("Key required for choice.", code="required")
        if (
            question.question_type
            and question.question_type not in Question.CHOICE_TYPES
        ):
            raise ValidationError(
                "Choices not permitted for questions of type %(question_type)s.",
                code="non-choice type",
                params={"question_type": question.question_type},
            )
        if question.weight and question.weight > 0 and not value_is_numeric(key):
            raise ValidationError(
                "The choice keys for a weighted question must be numeric. "
                'The value "%(key)s" is non-numeric.',
                code="non-numeric key",
                params={"key": key},
            )


class RubricResponse(models.Model):
    rubric = models.ForeignKey("Rubric", on_delete=models.CASCADE)

    def save(self, **kwargs):
        super(RubricResponse, self).save(**kwargs)
        if not self.questionresponse_set.exists():
            for ques in self.rubric.question_set.all():
                QuestionResponse.objects.create(rubric_response=self, question=ques)

    @property
    def ordered_questionresponse_set(self):
        return self.questionresponse_set.order_by("question__order")

    @property
    def has_response(self):
        text_response_empty = Q(text_response__isnull=True) | Q(text_response="")
        return self.questionresponse_set.exclude(
            text_response_empty, choice_response__isnull=True
        ).exists()

    @property
    def complete(self) -> bool:
        """bool: True if all required questions are answered. False otherwise."""
        return not self.questionresponse_set.filter(
            question__required=True,
            choice_response__isnull=True,
            text_response__isnull=True,
        ).exists()

    @property
    def question_response_dict(self):
        return {
            resp.question.pk: resp
            for resp in self.questionresponse_set.select_related("question").all()
        }

    @property
    def last_submitted(self):
        qs = self.questionresponse_set.all()
        return qs.aggregate(last_submitted=Max("last_submitted"))["last_submitted"]

    def score(self):
        score = 0
        for response in self.questionresponse_set.select_related("question").all():
            try:
                score += response.score()
            except TypeError:
                continue
        return score

    def question_answer_iter(self):
        for resp in self.ordered_questionresponse_set.select_related("question").all():
            yield resp.question.question_type, resp.question.description(), resp.response_external()

    def get_form_data(self):
        return {
            response.question.field_name(): response.response
            for response in self.question_response_dict.values()
        }

    @transaction.atomic
    def update_responses(self, updated_data):
        qr_dict = self.question_response_dict
        for key, value in updated_data.items():
            resp = qr_dict[key]
            resp.update_response(value)


class QuestionResponse(models.Model):
    rubric_response = models.ForeignKey("RubricResponse", on_delete=models.CASCADE)
    question = models.ForeignKey("Question", on_delete=models.CASCADE)
    choice_response = models.CharField(max_length=20, null=True, blank=True)
    text_response = models.TextField(null=True, blank=True)
    last_submitted = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return "{question}: {answer}".format(
            question=self.question.short_description, answer=self.response
        )

    @property
    def response(self):
        return QuestionType.get_instance(self.question).response(self)

    @property
    def question_answered(self):
        return QuestionType.get_instance(self.question).question_answered(self)

    def response_external(self):
        return QuestionType.get_instance(self.question).response_external(self)

    def update_response(self, value):
        QuestionType.get_instance(self.question).update_response(self, value)
        self.last_submitted = timezone.now()
        self.save()

    def score(self) -> float:
        """Return the weighted score of the question response.

        Obtained by multiplying the unweighted score by the weight of the
        question.

        """
        return QuestionType.get_instance(self.question).score(self)

    def unweighted_score(self) -> float:
        """Return the unweighted score for the question response."""
        return QuestionType.get_instance(self.question).unweighted_score(self)

    def clear_response(self):
        self.update_response(None)


class QuestionType(object):
    question = None

    @classmethod
    def get_instance(cls, question: Question):
        return QUESTION_TYPE_DICT.get(question.question_type, GenericQuestionType)(
            question
        )

    def __init__(self, question: Question):
        super(QuestionType, self).__init__()
        self.question = question

    def show_choices(self):
        return False

    def question_answered(self, response: QuestionResponse):
        return self.response(response)

    def response(self, response: QuestionResponse):
        raise NotImplementedError

    def response_external(self, response: QuestionResponse):
        raise NotImplementedError

    def update_response(self, response: QuestionResponse, value):
        raise NotImplementedError

    def score(self, response: QuestionResponse) -> float:
        raise NotImplementedError

    def unweighted_score(self, response: QuestionResponse) -> float:
        raise NotImplementedError


class GenericQuestionType(QuestionType):
    pass


class ChoiceSelectionMixin(object):
    def show_choices(self):
        return True


class SingleSelectionMixin(ChoiceSelectionMixin):
    def response(self, response: QuestionResponse):
        return response.choice_response

    def response_external(self, response: QuestionResponse):
        resp = response.choice_response
        if resp is None:
            return None
        choices = {key: value for key, value in self.question.choices()}

        return choices[resp]

    def update_response(self, response: QuestionResponse, value):
        response.choice_response = value

    def score(self, response: QuestionResponse) -> float:
        weight = float(self.question.weight)
        if weight == 0:
            return 0.0
        else:
            return self.unweighted_score(response) * weight

    def unweighted_score(self, response: QuestionResponse) -> float:
        try:
            value = float(response.choice_response)
        except (ValueError, TypeError):
            return 0.0
        else:
            return value


class SingleSelectQuestionType(SingleSelectionMixin, QuestionType):
    internal_name = "SINGLE SELECT"
    external_name = "Single Select"


class ScaleQuestionType(SingleSelectionMixin, QuestionType):
    internal_name = "SCALE"
    external_name = "Scale"


class MultiSelectQuestionType(ChoiceSelectionMixin, QuestionType):
    internal_name = "MULTI SELECT"
    external_name = "Multiple Select"

    def question_answered(self, response: QuestionResponse):
        return response.text_response

    def response(self, response: QuestionResponse):
        resp = response.text_response
        if not resp:
            return []
        return json.loads(resp)

    def response_external(self, response: QuestionResponse):
        resp = response.text_response
        if not resp:
            return []
        resp = json.loads(resp)
        choices = {key: value for key, value in self.question.choices()}

        return [choices[indv] for indv in resp]

    def update_response(self, response: QuestionResponse, value):
        if not value:
            response.text_response = ""
        else:
            response.text_response = json.dumps(value)

    def score(self, response: QuestionResponse) -> float:
        weight = float(self.question.weight)
        if weight == 0:
            return 0.0
        else:
            return self.unweighted_score(response) * weight

    def unweighted_score(self, response: QuestionResponse) -> float:
        responses = json.loads(response.text_response)
        value = 0.0
        for x in responses:
            try:
                value += float(x)
            except (ValueError, TypeError):
                continue
        return value


class LongTextQuestionType(QuestionType):
    internal_name = "LONG TEXT"
    external_name = "Long Text"

    def response(self, response: QuestionResponse):
        return response.text_response

    def response_external(self, response: QuestionResponse):
        return self.response(response)

    def update_response(self, response: QuestionResponse, value):
        response.text_response = value

    def score(self, response: QuestionResponse) -> float:
        raise TypeError(
            "Questions of type {0} cannot be scored".format(self.__class__.__name__)
        )

    def unweighted_score(self, response: QuestionResponse) -> float:
        raise TypeError(
            "Questions of type {0} cannot be scored".format(self.__class__.__name__)
        )


QUESTION_TYPE_DICT = {
    c.internal_name: c
    for c in (
        ScaleQuestionType,
        SingleSelectQuestionType,
        MultiSelectQuestionType,
        LongTextQuestionType,
    )
}
