import json

from django.db import models
from django.db import transaction
from django.db.models import Max
from django.utils import timezone


class Rubric(models.Model):
    name = models.CharField(
        max_length=200)

    def __str__(self):
        return self.name


class Question(models.Model):
    SCALE_TYPE = 'SCALE'
    SINGLE_SELECT_TYPE = 'SINGLE SELECT'
    MULTI_SELECT_TYPE = 'MULTI SELECT'
    LONG_TEXT = 'LONG TEXT'
    TYPES = (
        (SCALE_TYPE, 'Scale'),
        (SINGLE_SELECT_TYPE, 'Single Select'),
        (MULTI_SELECT_TYPE, 'Multi-Select'),
        (LONG_TEXT, 'Free Text (Long)')
    )
    CHOICE_TYPES = (SCALE_TYPE, SINGLE_SELECT_TYPE, MULTI_SELECT_TYPE)

    AUTO_SORT = 'A'
    MANUAL_SORT = 'M'
    SORT_CHOICES = (
        (AUTO_SORT, 'Auto'),
        (MANUAL_SORT, 'Manual')
    )

    rubric = models.ForeignKey(
        'Rubric',
        on_delete=models.CASCADE
    )
    order = models.PositiveSmallIntegerField(null=True, blank=True)
    short_description = models.CharField(
        max_length=200
    )
    long_description = models.TextField(null=True, blank=True)
    help_text = models.TextField(null=True, blank=True)
    weight = models.DecimalField(
        max_digits=4,
        decimal_places=3,
        null=True
    )
    question_type = models.CharField(
        max_length=20,
        choices=TYPES
    )
    choice_sort = models.CharField(
        max_length=1,
        choices=SORT_CHOICES
    )
    required = models.BooleanField(
        default=True
    )

    ordering = ('rubric', 'order', 'short_description')

    def __init__(self, *args, **kwargs):
        # __init__ is run when objects are retrieved from the database
        # in addition to when they are created.
        super(Question, self).__init__(*args, **kwargs)
        if not self.order:
            self.order = self._get_next_order()
            
    def save(self, **kwargs):
        if not self.is_allowed_type(self.question_type):
            raise ValueError(
                'question_type was %s. Should be one of %s.' %
                (self.question_type, self.available_types()))

        if not self.is_allowed_sort(self.choice_sort):
            raise ValueError(
                'choice_sort was %s. Should be one of %s.' %
                (self.choice_sort, self.sort_options()))

        QuestionType.get_instance(self).perform_type_specific_save_checks()

        super(Question, self).save(**kwargs)

    def _get_next_order(self):
        try:
            max_order = Question.objects.filter(
                rubric=self.rubric).aggregate(models.Max('order'))['order__max']
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
            return '-'

    def description(self):
        return self.long_description or self.short_description

    def choices(self):
        for choice in self.choice_set.all():
            yield (choice.key, choice.description)

    def field_name(self):
        return 'question_%s' % self.pk

    def add_choice(self, key, description, order=None):
        choice = Choice(question=self, key=key, description=description)
        if order:
            choice.order = order
        choice.save()
        return choice

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


class Choice(models.Model):
    question = models.ForeignKey(
        'Question',
        on_delete=models.CASCADE
    )
    order = models.PositiveSmallIntegerField(null=True, blank=True)
    key = models.CharField(max_length=20)
    description = models.CharField(max_length=200)

    ordering = ('question', 'order', 'key')

    def __init__(self, *args, **kwargs):
        # __init__ is run when objects are retrieved from the database
        # in addition to when they are created.
        super(Choice, self).__init__(*args, **kwargs)
        if not self.order:
            self.order = self._get_next_order()
                
    def save(self, **kwargs):
        if self.question.question_type not in self.question.CHOICE_TYPES:
            raise AttributeError(
                'Choices not permitted for questions of type %s' % 
                self.question.question_type)

        super(Choice, self).save(**kwargs)

    def _get_next_order(self):
        try:
            max_order = Choice.objects.filter(
                question=self.question).aggregate(models.Max('order'))['order__max']
        except Question.DoesNotExist:
            return

        if max_order:
            return max_order + 1
        else:
            return 1

    def __str__(self):
        return self.description


class RubricResponse(models.Model):
    rubric = models.ForeignKey(
        'Rubric',
        on_delete=models.CASCADE
    )

    def save(self, **kwargs):
        super(RubricResponse, self).save(**kwargs)
        if not self.questionresponse_set.exists():
            for ques in self.rubric.question_set.all():
                QuestionResponse.objects.create(rubric_response=self, question=ques)

    @property
    def has_response(self):
        return self.questionresponse_set.exclude(
            choice_response__isnull=True, text_response__isnull=True).exists()

    @property
    def question_response_dict(self):
        return {resp.question.pk: resp
                for resp in self.questionresponse_set.select_related('question').all()}

    @property
    def last_submitted(self):
        qs = self.questionresponse_set.all()
        return qs.aggregate(last_submitted=Max('last_submitted'))['last_submitted']

    def score(self):
        score = 0
        for response in self.questionresponse_set.select_related('question').all():
            try:
                score += response.score()
            except TypeError:
                continue
        return score

    def question_answer_iter(self):
        for resp in self.questionresponse_set.select_related('question').all():
            yield resp.question.question_type, resp.question.description(), resp.response_external()

    def get_form_data(self):
        return {response.question.field_name(): response.response
                for response in self.question_response_dict.values()}

    @transaction.atomic
    def update_responses(self, updated_data):
        qr_dict = self.question_response_dict
        for key, value in updated_data.items():
            resp = qr_dict[key]
            resp.update_response(value)


class QuestionResponse(models.Model):
    rubric_response = models.ForeignKey(
        'RubricResponse',
        on_delete=models.CASCADE
    )
    question = models.ForeignKey(
        'Question',
        on_delete=models.CASCADE
    )
    choice_response = models.CharField(
        max_length=20,
        null=True,
        blank=True
    )
    text_response = models.TextField(null=True, blank=True)
    last_submitted = models.DateTimeField(
        null=True, blank=True
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

    def score(self):
        return QuestionType.get_instance(self.question).score(self)
    
    
class QuestionType(object):
    @classmethod
    def get_instance(cls, question: Question):
        return QUESTION_TYPE_DICT.get(question.question_type, GenericQuestionType)(question)

    def __init__(self, question):
        super(QuestionType, self).__init__()
        self.question = question

    def perform_type_specific_save_checks(self):
        pass

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
        try:
            value = float(response.choice_response)
        except ValueError:
            return 0.0
        else:
            return value * weight


class SingleSelectQuestionType(SingleSelectionMixin, QuestionType):
    internal_name = 'SINGLE SELECT'
    external_name = 'Single Select'


class ScaleQuestionType(SingleSelectionMixin, QuestionType):
    internal_name = 'SCALE'
    external_name = 'Scale'


class MultiSelectQuestionType(ChoiceSelectionMixin, QuestionType):
    internal_name = 'MULTI SELECT'
    external_name = 'Multiple Select'

    def question_answered(self, response: QuestionResponse):
        return response.choice_response

    def response(self, response: QuestionResponse):
        resp = response.choice_response
        if not resp:
            return []
        return json.loads(resp)

    def response_external(self, response: QuestionResponse):
        resp = response.choice_response
        if not resp:
            return []
        resp = json.loads(resp)
        choices = {key: value for key, value in self.question.choices()}

        return [choices[indv] for indv in resp]

    def update_response(self, response: QuestionResponse, value):
        response.choice_response = json.dumps(value)

    def score(self, response: QuestionResponse) -> float:
        weight = float(self.question.weight)
        if weight == 0:
            return 0.0

        responses = json.loads(response.choice_response)
        value = 0
        for x in responses:
            try:
                value += float(x)
            except ValueError:
                continue
        return value * float(self.question.weight)


class LongTextQuestionType(QuestionType):
    internal_name = 'LONG TEXT'
    external_name = 'Long Text'

    def perform_type_specific_save_checks(self):
        if self.question.weight and self.question.weight > 0:
            raise ValueError(
                'A weight greater than 0 not allowed for questions of type %s' %
                self.internal_name)

    def response(self, response: QuestionResponse):
        return response.text_response

    def response_external(self, response: QuestionResponse):
        return self.response(response)

    def update_response(self, response: QuestionResponse, value):
        response.text_response = value

    def score(self, response: QuestionResponse) -> float:
        raise TypeError('Questions of type {0} cannot be scored'.format(
            self.__class__.__name__))


QUESTION_TYPE_DICT = {c.internal_name: c for c in (ScaleQuestionType,
                                                   SingleSelectQuestionType,
                                                   MultiSelectQuestionType,
                                                   LongTextQuestionType)}
