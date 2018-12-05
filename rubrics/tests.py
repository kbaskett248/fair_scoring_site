import random
import unittest
from contextlib import contextmanager
from datetime import datetime

from django.core.exceptions import ValidationError
from django.utils import timezone
from hypothesis import given, example, assume
from hypothesis.extra.django import TestCase as HypTestCase
from hypothesis.extra.django.models import models
from hypothesis.searchstrategy import SearchStrategy
from hypothesis.strategies import one_of, sampled_from, text, lists, integers, \
    just, tuples, none
from model_mommy import mommy

from rubrics.fixtures import make_test_rubric
from rubrics.forms import ChoiceForm, QuestionForm
from rubrics.models import Rubric, Question, Choice, RubricResponse, QuestionResponse, value_is_numeric


def fixed_decimals(min_value: float=0, max_value: float=1, num_decimals=3) -> SearchStrategy:
    power_of_ten = 10 ** num_decimals
    return integers(min_value=(min_value*power_of_ten),
                    max_value=(max_value*power_of_ten)).map(lambda x: x / power_of_ten)


def sane_text(min_size=0, max_size=1024, average_size=None) -> SearchStrategy:
    return text(alphabet=[chr(i) for i in range(33, 126)],
                min_size=min_size, max_size=max_size, average_size=average_size)


def question_type() -> SearchStrategy:
    return sampled_from(Question.CHOICE_TYPES)


def question_type_and_weight() -> SearchStrategy:
    return one_of(
        tuples(sampled_from(Question.CHOICE_TYPES),
               fixed_decimals()),
        tuples(sampled_from(sorted(set(Question.available_types()) - set(Question.CHOICE_TYPES))),
               just(0))
    )


def questions(rubric: Rubric) -> SearchStrategy:
    def create_question(type_and_weight: tuple) -> SearchStrategy:
        return models(Question,
                      rubric=just(rubric),
                      question_type=just(type_and_weight[0]),
                      weight=just(type_and_weight[1]),
                      short_description=sane_text())
    return question_type_and_weight().flatmap(create_question)


def rubric_with_questions(min_questions: int=None, max_questions: int=None,
                          average_questions: int=10) -> SearchStrategy:
    def add_questions(rubric: Rubric) -> SearchStrategy:
        return lists(elements=questions(rubric),
                     min_size=min_questions,
                     max_size=max_questions,
                     average_size=average_questions,
                     unique=True).flatmap(lambda _: just(rubric))
    return models(Rubric).flatmap(add_questions)


def create_rubric_with_questions_and_choices():
    rubric = mommy.make(Rubric)
    for _ in range(0, 10):
        required = bool(random.getrandbits(1))
        question = mommy.make(Question, rubric=rubric, required=required)
        if question.show_choices():
            for a in range(0, 5):
                mommy.make(Choice, question=question)

    return rubric


class TestBase(HypTestCase):
    @contextmanager
    def assertNoException(self, exception_type):
        try:
            yield
        except exception_type:
            self.fail('%s exception type raised' % exception_type)


class RubricTests(HypTestCase):
    @given(sane_text())
    def test_create_rubric(self, name: str):
        rubric = Rubric.objects.create(name=name)
        self.assertEqual(rubric.name, name)
        self.assertQuerysetEqual(Rubric.objects.all(), ['<Rubric: %s>' % name])


class QuestionTests(HypTestCase):
    @classmethod
    def setUpClass(cls):
        super(QuestionTests, cls).setUpClass()
        cls.rubric = create_rubric_with_questions_and_choices()

    def test_is_allowed_type(self):
        self.assertTrue(Question.is_allowed_type(Question.LONG_TEXT))
        self.assertFalse(Question.is_allowed_type("Some Google Type"))

    def test_is_allowed_sort(self):
        self.assertTrue(Question.is_allowed_sort(Question.AUTO_SORT))
        self.assertFalse(Question.is_allowed_sort("Some Google Sort"))

    def test_num_choices(self):
        for number, question in enumerate(self.rubric.question_set.all(), start=1):
            with self.subTest('Question %(number)s', number=number):
                if question.show_choices():
                    self.assertIsInstance(question.num_choices_display(), int)
                    self.assertEqual(question.num_choices_display(), 5)
                else:
                    self.assertEqual(question.num_choices_display(), '-')

    @given(question_type=sane_text())
    def test_invalid_question_type_raises_error(self, question_type):
        with self.assertRaises(ValidationError):
            mommy.make(Question, rubric=self.rubric, question_type=question_type)

    @given(sort_option=one_of(sane_text().filter(lambda x: x != 'A' and x != 'M'),
                              none()))
    def test_invalid_sort_option_raises_error(self, sort_option):
        with self.assertRaises(ValidationError,
                               msg="No error raised for sort_option {}".format(sort_option)):
            mommy.make(Question, rubric=self.rubric, question_type=Question.LONG_TEXT,
                       choice_sort=sort_option)

    @given(fixed_decimals(min_value=0.001))
    def test_unweighted_question_type_with_non_zero_weight_raises_value_error(self, weight):
        with self.assertRaises(ValidationError):
            mommy.make(Question, rubric=self.rubric, question_type=Question.LONG_TEXT,
                       weight=weight)

    def test_add_choice(self):
        def add_choices(question):
            question.add_choice(1, 'Low')
            question.add_choice(10, 'High')

        with self.subTest('%(type)s question', type=Question.SCALE_TYPE):
            question = mommy.make(Question, question_type=Question.SCALE_TYPE, rubric=self.rubric)
            add_choices(question)
            self.assertQuerysetEqual(question.choice_set.order_by('description').all(),
                                     ['<Choice: High>', '<Choice: Low>'])

        with self.subTest('%(type)s question', type=Question.LONG_TEXT):
            question = mommy.make(Question, question_type=Question.LONG_TEXT, rubric=self.rubric)
            with self.assertRaises(ValidationError):
                add_choices(question)

    @given(question_type_and_weight(), question_type_and_weight())
    def test_question_type_changed(self, q1: (str, float), q2: (str, float)):
        question = mommy.make(Question, question_type=q1[0], weight=0)  # type: Question
        self.assertEqual(question.question_type, q1[0])
        question.question_type = q2[0]
        self.assertEqual(question.question_type, q2[0])

        if q1[0] == q2[0]:
            self.assertFalse(question.question_type_changed())
        else:
            self.assertTrue(question.question_type_changed())

    @given(question_type_and_weight(), question_type_and_weight())
    def test_question_type_changed_compatibility(self, q1: (str, float), q2: (str, float)):
        compatible_types = (Question.SCALE_TYPE, Question.SINGLE_SELECT_TYPE)
        question = mommy.make(Question, question_type=q1[0], weight=0)  # type: Question
        self.assertEqual(question.question_type, q1[0])
        question.question_type = q2[0]
        self.assertEqual(question.question_type, q2[0])

        if q1[0] == q2[0]:
            self.assertFalse(question.question_type_changed_compatibility())
        elif (q1[0] in compatible_types) and (q2[0] in compatible_types):
            self.assertFalse(question.question_type_changed_compatibility())
        else:
            self.assertTrue(question.question_type_changed_compatibility())


class QuestionFormTests(HypTestCase):
    @classmethod
    def setUpClass(cls):
        super(QuestionFormTests, cls).setUpClass()
        cls.rubric = mommy.make(Rubric)  # type: Rubric
        cls.data = {'rubric': cls.rubric.pk,
                    'order': 1,
                    'short_description': 'Test Question',
                    'long_description': 'This question is very important',
                    'help_text': 'This is help text for the question',
                    'weight': 0,
                    'question_type': Question.SCALE_TYPE,
                    'choice_sort': Question.MANUAL_SORT,
                    'required': True}
        data = cls.data.copy()
        data['rubric'] = cls.rubric
        cls.question = Question.objects.create(**data)  # type: Question

    def get_test_data_and_form(self, updated_data: dict, instance: Question=None) -> tuple:
        data = self.data.copy()
        if updated_data:
            data.update(updated_data)
        form = QuestionForm(data, instance=instance)
        return data, form

    def success_test(self, instance: Question=None, **updated_data):
        data, form = self.get_test_data_and_form(updated_data, instance=instance)
        self.assertTrue(form.is_valid())
        question = form.save(commit=False)
        for key, value in data.items():
            if key == 'rubric':
                self.assertEqual(value, question.rubric.pk)
            else:
                self.assertEqual(value, getattr(question, key, None))

    def failed_test(self, instance: Question=None, **updated_data):
        data, form = self.get_test_data_and_form(updated_data, instance=instance)
        self.assertFalse(form.is_valid())
        with self.assertRaises(ValueError):
            form.save(commit=False)

    def test_valid_data(self):
        self.success_test()

    def test_invalid_question_type(self):
        self.failed_test(question_type='invalid question type')

    def test_invalid_sort(self):
        self.failed_test(choice_sort='Q')

    def test_negative_weight(self):
        self.failed_test(weight=-0.5)

    def test_weight_with_non_choice_type(self):
        self.failed_test(weight=0.5, question_type=Question.LONG_TEXT)

    def test_instance_with_numeric_choices_and_zero_weight(self):
        self.question.weight = 1
        self.question.save()
        mommy.make(Choice, question=self.question, key='1')
        self.success_test(instance=self.question, weight=0)

    def test_instance_with_numeric_choices_and_positive_weight(self):
        self.question.weight = 0
        self.question.save()
        mommy.make(Choice, question=self.question, key='1')
        self.success_test(instance=self.question, weight=1)

    def test_instance_with_non_numeric_choices_and_zero_weight(self):
        self.question.weight = 0
        self.question.save()
        mommy.make(Choice, question=self.question, key='test')
        self.success_test(instance=self.question, weight=0)

    def test_instance_with_non_numeric_choices_and_positive_weight(self):
        self.question.weight = 0
        self.question.save()
        mommy.make(Choice, question=self.question, key='test')
        self.failed_test(instance=self.question, weight=1)


class ChoiceTests(TestBase):
    @classmethod
    def setUpClass(cls):
        super(ChoiceTests, cls).setUpClass()
        cls.question = mommy.make(Question)  # type: Question

    def choice_test_with_positive_weight(self, key):
        self.question.weight = 1.000
        kwargs = {'question': self.question, 'order': 1, 'key': key, 'description': 'description'}
        if not value_is_numeric(key):
            with self.assertRaises(ValidationError):
                Choice.validate(**kwargs)
            c = Choice(**kwargs)
            with self.assertRaises(ValidationError):
                c.save()
        else:
            with self.assertNoException(ValidationError):
                Choice.validate(question=self.question, order=1, key=key, description='description')
            c = Choice(**kwargs)
            with self.assertNoException(ValidationError):
                c.save()

    def choice_test_with_zero_weight(self, key):
        self.question.weight = 0
        kwargs = {'question': self.question, 'order': 1, 'key': key, 'description': 'description'}
        with self.assertNoException(ValidationError):
            Choice.validate(**kwargs)
        c = Choice(**kwargs)
        with self.assertNoException(ValidationError):
            c.save()

    @given(sane_text(min_size=1))
    def test_scale_question_with_positive_weight(self, key):
        self.question.question_type = Question.SCALE_TYPE
        self.choice_test_with_positive_weight(key)

    @given(sane_text(min_size=1))
    def test_scale_question_with_zero_weight(self, key):
        self.question.question_type = Question.SCALE_TYPE
        self.choice_test_with_zero_weight(key)

    @given(sane_text(min_size=1))
    def test_single_select_question_with_positive_weight(self, key):
        self.question.question_type = Question.SINGLE_SELECT_TYPE
        self.choice_test_with_positive_weight(key)

    @given(sane_text(min_size=1))
    def test_single_select_question_with_zero_weight(self, key):
        self.question.question_type = Question.SINGLE_SELECT_TYPE
        self.choice_test_with_zero_weight(key)

    @given(sane_text(min_size=1))
    def test_multi_select_question_with_positive_weight(self, key):
        self.question.question_type = Question.MULTI_SELECT_TYPE
        self.choice_test_with_positive_weight(key)

    @given(sane_text(min_size=1))
    def test_multi_select_question_with_zero_weight(self, key):
        self.question.question_type = Question.MULTI_SELECT_TYPE
        self.choice_test_with_zero_weight(key)

    def test_long_text_question_disallows_choices(self):
        self.question.question_type = Question.LONG_TEXT
        self.question.weight = 0
        kwargs = {'question': self.question, 'order': 1, 'key': 'key', 'description': 'description'}
        with self.assertRaises(ValidationError):
            Choice.validate(**kwargs)
        c = Choice(**kwargs)
        with self.assertRaises(ValidationError):
            c.save()


class ChoiceFormTests(HypTestCase):
    def setUp(self):
        self.question = mommy.make(Question)  # type: Question

    def update_question(self, question_type, weight):
        self.question.question_type = question_type
        self.question.weight = weight
        self.question.save()

    def success_test(self, data):
        form = ChoiceForm(data)
        self.assertTrue(form.is_valid())
        choice = form.save()
        self.assertEqual(choice.order, data['order'])
        self.assertEqual(choice.key, data['key'])
        self.assertEqual(choice.description, data['description'])

    def failed_test(self, data):
        form = ChoiceForm(data)
        self.assertFalse(form.is_valid())
        with self.assertRaises(ValueError):
            form.save()

    def test_scale_question_with_positive_weight(self):
        self.update_question(Question.SCALE_TYPE, 1.000)

        data = {'question': self.question.pk, 'order': 1, 'key': '1', 'description': 'description'}
        self.success_test(data)

        data = {'question': self.question.pk, 'order': 2, 'key': 'key', 'description': 'description'}
        self.failed_test(data)

    def test_scale_question_with_zero_weight(self):
        self.update_question(Question.SCALE_TYPE, 0)

        data = {'question': self.question.pk, 'order': 1, 'key': '1', 'description': 'description'}
        self.success_test(data)

        data = {'question': self.question.pk, 'order': 2, 'key': 'key', 'description': 'description'}
        self.success_test(data)

    def test_single_select_question_with_positive_weight(self):
        self.update_question(Question.SINGLE_SELECT_TYPE, 1.000)

        data = {'question': self.question.pk, 'order': 1, 'key': '1', 'description': 'description'}
        self.success_test(data)

        data = {'question': self.question.pk, 'order': 2, 'key': 'key', 'description': 'description'}
        self.failed_test(data)

    def test_single_select_question_with_zero_weight(self):
        self.update_question(Question.SINGLE_SELECT_TYPE, 0)

        data = {'question': self.question.pk, 'order': 1, 'key': '1', 'description': 'description'}
        self.success_test(data)

        data = {'question': self.question.pk, 'order': 2, 'key': 'key', 'description': 'description'}
        self.success_test(data)

    def test_multi_select_question_with_positive_weight(self):
        self.update_question(Question.MULTI_SELECT_TYPE, 1.000)

        data = {'question': self.question.pk, 'order': 1, 'key': '1', 'description': 'description'}
        self.success_test(data)

        data = {'question': self.question.pk, 'order': 2, 'key': 'key', 'description': 'description'}
        self.failed_test(data)

    def test_multi_select_question_with_zero_weight(self):
        self.update_question(Question.MULTI_SELECT_TYPE, 0)

        data = {'question': self.question.pk, 'order': 1, 'key': '1', 'description': 'description'}
        self.success_test(data)

        data = {'question': self.question.pk, 'order': 2, 'key': 'key', 'description': 'description'}
        self.success_test(data)

    def test_long_text_question_with_positive_weight(self):
        with self.assertRaises(ValidationError):
            self.update_question(Question.LONG_TEXT, 1.000)

    def test_long_text_question_with_zero_weight(self):
        self.update_question(Question.LONG_TEXT, 0)

        data = {'question': self.question.pk, 'order': 1, 'key': '1', 'description': 'description'}
        self.failed_test(data)

        data = {'question': self.question.pk, 'order': 2, 'key': 'key', 'description': 'description'}
        self.failed_test(data)


class RubricResponseTests(HypTestCase):
    def make_rubric_response(self, rubric=None):
        if not rubric:
            rubric = create_rubric_with_questions_and_choices()
        rub_resp = RubricResponse(rubric=rubric)
        rub_resp.save()
        return rub_resp

    def test_has_response(self, rubric=None):
        if not rubric:
            rubric = create_rubric_with_questions_and_choices()

        rubric_response = self.make_rubric_response(rubric=rubric)
        self.assertFalse(rubric_response.has_response)

        q_resp = rubric_response.questionresponse_set.first()
        self.assertIsNotNone(q_resp)
        self.assertFalse(q_resp.question_answered)

        self.answer_question(q_resp)
        self.assertTrue(rubric_response.has_response)
        self.assertTrue(q_resp.question_answered)

    def test_complete(self, rubric=None):
        if not rubric:
            rubric = create_rubric_with_questions_and_choices()

        rubric_response = self.make_rubric_response(rubric=rubric)
        self.assertFalse(rubric_response.complete)

        q_resp = rubric_response.questionresponse_set.first()
        self.assertIsNotNone(q_resp)
        self.assertFalse(q_resp.question_answered)

        self.answer_question(q_resp)
        self.assertTrue(q_resp.question_answered)
        self.assertFalse(rubric_response.complete)

        for q_resp in rubric_response.questionresponse_set.filter(question__required=True):
            self.answer_question(q_resp)

        self.assertTrue(rubric_response.complete)

    @staticmethod
    def answer_question(question_resp):
        question = question_resp.question
        if question.question_type == Question.LONG_TEXT:
            question_resp.update_response('This is some long text')
        elif question.question_type == Question.MULTI_SELECT_TYPE:
            choices = [choice[0] for choice in question.choices()]
            question_resp.update_response(choices)
        else:
            question_resp.update_response(next(question.choices()))

    def test_last_submitted(self):
        rub_response = make_rubric_response()

        self.assertIsNone(rub_response.last_submitted)

        answer_rubric_response(rub_response)

        self.assertIsNotNone(rub_response.last_submitted)
        self.assertIsInstance(rub_response.last_submitted, datetime)
        elapsed_seconds = (timezone.now() - rub_response.last_submitted).seconds
        self.assertEqual(elapsed_seconds, 0)

    def test_score(self):
        rub_response = make_rubric_response()

        self.assertEqual(rub_response.score(), 0,
                         "Score is not zero before answering the Rubric")

        answer_rubric_response(rub_response)

        self.assertAlmostEqual(rub_response.score(), 1.665, 3,
                               "Score incorrect after answering the Rubric")


def make_rubric_response(rubric=None):
    rubric = rubric or make_test_rubric()

    return mommy.make(RubricResponse, rubric=rubric)


def answer_rubric_response(rubric_response):
    for q_resp in rubric_response.questionresponse_set.all():
        if q_resp.question.question_type == Question.MULTI_SELECT_TYPE:
            q_resp.update_response(['1', '2'])
        elif q_resp.question.question_type == Question.LONG_TEXT:
            q_resp.update_response('This is a long text response.\nThis is a second line')
        else:
            q_resp.update_response('1')


class QuestionResponseTests(HypTestCase):
    def test_empty_responses(self):
        rub_response = make_rubric_response()
        for response in rub_response.questionresponse_set.select_related('question').all():
            if response.question.question_type == Question.MULTI_SELECT_TYPE:
                self.assertEqual(
                    response.response, [],
                    'Empty response not equal to %s for question type %s' %
                    ([], response.question.question_type)
                )
            else:
                self.assertEqual(
                    response.response, None,
                    'Empty response not equal to %s for question type %s' %
                    (None, response.question.question_type))

    def test_empty_responses_external(self):
        rub_response = make_rubric_response()
        for response in rub_response.questionresponse_set.select_related('question').all():
            if response.question.question_type == Question.MULTI_SELECT_TYPE:
                self.assertEqual(
                    response.response_external(), [],
                    'Empty external response not equal to %s for question type %s' %
                    ([], response.question.question_type)
                )
            else:
                self.assertEqual(
                    response.response_external(), None,
                    'Empty external response not equal to %s for question type %s' %
                    (None, response.question.question_type))

    def generic_response_test(self, check_response: callable):
        rub_response = make_rubric_response()
        answer_rubric_response(rub_response)

        for response in rub_response.questionresponse_set.select_related('question').all():
            check_response(response)

    def test_response(self):
        value_dict = {Question.LONG_TEXT: 'This is a long text response.\nThis is a second line',
                      Question.MULTI_SELECT_TYPE: ['1', '2'],
                      'default': '1'}

        def check_response(response: QuestionResponse):
            value = value_dict.get(response.question.question_type, value_dict['default'])
            self.assertEqual(
                response.response, value,
                'Response not equal to %s for question type %s' %
                (value, response.question.question_type))

        self.generic_response_test(check_response)

    def test_response_external(self):
        value_dict = {Question.LONG_TEXT: 'This is a long text response.\nThis is a second line',
                      Question.MULTI_SELECT_TYPE: ['Choice 1', 'Choice 2'],
                      'default': 'Choice 1'}

        def check_response(response: QuestionResponse):
            value = value_dict.get(response.question.question_type, value_dict['default'])
            self.assertEqual(
                response.response_external(), value,
                'Response not equal to %s for question type %s' %
                (value, response.question.question_type))

        self.generic_response_test(check_response)

    def test_score_and_unweighted_score(self):
        def check_response(response: QuestionResponse):
            q_type = response.question.question_type
            if q_type == Question.LONG_TEXT:
                with self.assertRaises(TypeError):
                    response.score()
            elif q_type == Question.MULTI_SELECT_TYPE:
                self.assertAlmostEqual(response.score(), 0.999, places=3)
                self.assertAlmostEqual(response.unweighted_score(), 3)
            else:
                self.assertAlmostEqual(response.score(), 0.333)
                self.assertAlmostEqual(response.unweighted_score(), 1)

        self.generic_response_test(check_response)

    # Choice was updated so that non-numeric choices could not be saved for weighted questions.
    @unittest.expectedFailure
    def test_score_for_non_numeric_choices(self):
        rubric = mommy.make(Rubric, name="Test Rubric")
        rub_response = make_rubric_response(rubric)

        question_type = Question.SINGLE_SELECT_TYPE
        question = mommy.make(Question,
                              rubric=rubric,
                              short_description='Question %s' % question_type,
                              long_description='This is for question %s' % question_type,
                              help_text='This is help text for question %s' % question_type,
                              weight=1,
                              question_type=question_type,
                              required=True)
        choices = mommy.make(Choice, _quantity=4, question=question)
        q_resp = mommy.make(QuestionResponse,
                            rubric_response=rub_response,
                            question=question)
        q_resp.update_response(choices[0].key)
        self.assertEqual(q_resp.score(), 0,
                         msg='Score should be zero for questions with non-numeric choices')

        question_type = Question.MULTI_SELECT_TYPE
        question = mommy.make(Question,
                              rubric=rubric,
                              short_description='Question %s' % question_type,
                              long_description='This is for question %s' % question_type,
                              help_text='This is help text for question %s' % question_type,
                              weight=1,
                              question_type=question_type,
                              required=True)
        choices = mommy.make(Choice, _quantity=4, question=question)
        q_resp = mommy.make(QuestionResponse,
                            rubric_response=rub_response,
                            question=question)
        q_resp.update_response([choices[0].key, choices[1].key])
        self.assertEqual(q_resp.score(), 0,
                         msg='Score should be zero for questions with non-numeric choices')

    def test_last_saved_date(self):
        rub_response = make_rubric_response()

        for response in rub_response.questionresponse_set.select_related('question').all():
            self.assertIsNone(response.last_submitted)

        answer_rubric_response(rub_response)
        now = timezone.now()

        for response in rub_response.questionresponse_set.select_related('question').all():
            self.assertIsNotNone(response.last_submitted)
            self.assertIsInstance(response.last_submitted, datetime)
            elapsed_seconds = (now - response.last_submitted).seconds
            self.assertEqual(elapsed_seconds, 0)

    def test_clear_response(self):
        rub_response = make_rubric_response()
        answer_rubric_response(rub_response)

        for response in rub_response.questionresponse_set.all():
            with self.subTest(response.question.question_type):
                self.assertTrue(response.question_answered)
                response.clear_response()
                self.assertFalse(response.question_answered)

    def test_new_question_is_added_to_response(self):
        rub_response = make_rubric_response()  # type: RubricResponse

        question = mommy.make(Question, rubric=rub_response.rubric, short_description="Additional test question")  # type: Question

        self.assertTrue(rub_response.questionresponse_set\
                        .filter(question__short_description="Additional test question")\
                        .exists())

        response = rub_response.questionresponse_set\
                   .get(question__short_description="Additional test question")  # type: QuestionResponse
        self.assertEqual(question, response.question)

    def test_deleted_question_is_removed_from_response(self):
        rub_response = make_rubric_response()  # type: RubricResponse
        num_question_responses = rub_response.questionresponse_set.count()

        question = rub_response.questionresponse_set.first().question  # type: Question

        question.delete()
        self.assertEqual(rub_response.questionresponse_set.count(),
                         num_question_responses-1)
        self.assertQuerysetEqual(rub_response.questionresponse_set.all(),
                                 ['Question SINGLE SELECT', 'Question MULTI SELECT', 'Question LONG TEXT'],
                                 transform=lambda x: x.question.__str__(),
                                 ordered=False)


class QuestionResponseClearingTests(HypTestCase):
    @classmethod
    def setUpClass(cls):
        super(QuestionResponseClearingTests, cls).setUpClass()
        cls.rubric = make_test_rubric()

    def setUp(self):
        super(QuestionResponseClearingTests, self).setUp()
        self.rub_response = make_rubric_response(self.rubric)
        answer_rubric_response(self.rub_response)

    def get_question_and_response(self, question_type: str) -> (Question, QuestionResponse):
        question = self.rub_response.rubric.question_set \
            .filter(question_type=question_type) \
            .first()  # type: Question
        response = self.rub_response.questionresponse_set \
            .get(question_id=question.id)  # type: QuestionResponse

        self.assertTrue(response.question_answered)

        return question, response

    def get_choice_and_response(self, question_type: str) -> (Choice, QuestionResponse):
        question, response = self.get_question_and_response(question_type)
        choice = question.choice_set.first()  # type: Choice
        return choice, response

    @staticmethod
    def update_question_type(question: Question, new_type: str) -> None:
        question.question_type = new_type
        question.save()

    @staticmethod
    def refresh_response(response: QuestionResponse) -> QuestionResponse:
        # Refreshing the response since refresh_from_db doesn't seem to work
        return QuestionResponse.objects.get(id=response.id)  # type: QuestionResponse

    @contextmanager
    def assertOnlyResponseForChoiceCleared(self, question_type: str):
        choice, response = self.get_choice_and_response(question_type)
        yield choice
        self.assertOnlyGivenResponseCleared(response)

    def assertOnlyGivenResponseCleared(self, response: QuestionResponse) -> None:
        for r in self.rub_response.questionresponse_set.all():
            if r.pk == response.pk:
                self.assertFalse(r.question_answered)
            else:
                self.assertTrue(r.question_answered)

    def assertNoResponsesCleared(self):
        for r in self.rub_response.questionresponse_set.all():
            self.assertTrue(r.question_answered)

    @given(question_type())
    def test_clear_responses_when_question_type_changed(self, new_type):
        question, response = self.get_question_and_response(Question.LONG_TEXT)
        self.update_question_type(question, new_type)

        if new_type == Question.LONG_TEXT:
            self.assertNoResponsesCleared()
        else:
            self.assertOnlyGivenResponseCleared(response)

    def test_responses_are_not_cleared_for_special_case(self):
        # Scale type and Single select type are the same with different widgets, so nothing
        # is cleared in this special case.
        for starting_type, new_type in ((Question.SCALE_TYPE, Question.SINGLE_SELECT_TYPE),
                                        (Question.SINGLE_SELECT_TYPE, Question.SCALE_TYPE)):
            with self.subTest('{} -> {}'.format(starting_type, new_type)):
                question, response = self.get_question_and_response(starting_type)
                self.update_question_type(question, new_type)
                self.assertNoResponsesCleared()

    @given(question_type().filter(lambda x: x in Question.CHOICE_TYPES))
    def test_clear_responses_when_choice_changes(self, question_type):
        with self.assertOnlyResponseForChoiceCleared(question_type) as choice:
            choice.key = 10000
            choice.save()

    @given(question_type().filter(lambda x: x in Question.CHOICE_TYPES))
    def test_clear_responses_when_choice_deleted(self, question_type):
        with self.assertOnlyResponseForChoiceCleared(question_type) as choice:
            choice.delete()

    @given(question_type().filter(lambda x: x in Question.CHOICE_TYPES))
    def test_clear_responses_when_choice_added(self, question_type):
        with self.assertOnlyResponseForChoiceCleared(question_type) as choice:
            mommy.make(Choice, question=choice.question, key=10000)
