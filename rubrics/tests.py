from datetime import datetime

from django.utils import timezone
from hypothesis import given
from hypothesis.extra.django import TestCase as HypTestCase
from hypothesis.extra.django.models import models
from hypothesis.searchstrategy import SearchStrategy
from hypothesis.strategies import one_of, sampled_from, text, lists, integers, \
    just, tuples, none
from model_mommy import mommy

from rubrics.models import Rubric, Question, Choice, RubricResponse, QuestionResponse


def fixed_decimals(min_value: float=0, max_value: float=1, num_decimals=3) -> SearchStrategy:
    power_of_ten = 10 ** num_decimals
    return integers(min_value=(min_value*power_of_ten),
                    max_value=(max_value*power_of_ten)).map(lambda x: x / power_of_ten)


def sane_text(min_size=None, max_size=None, average_size=None) -> SearchStrategy:
    return text(alphabet=[chr(i) for i in range(33, 126)],
                min_size=min_size, max_size=max_size, average_size=average_size)


def question_type_and_weight() -> SearchStrategy:
    return one_of(
        tuples(sampled_from(Question.CHOICE_TYPES),
               fixed_decimals()),
        tuples(sampled_from(set(Question.available_types()) - set(Question.CHOICE_TYPES)),
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
        question = mommy.make(Question, rubric=rubric)
        if question.show_choices():
            for a in range(0, 5):
                mommy.make(Choice, question=question)

    return rubric


class RubricTests(HypTestCase):
    @given(sane_text())
    def test_create_rubric(self, name: str):
        rubric = Rubric.objects.create(name=name)
        self.assertEqual(rubric.name, name)
        self.assertQuerysetEqual(Rubric.objects.all(), ['<Rubric: %s>' % name])


class QuestionTests(HypTestCase):
    def test_is_allowed_type(self):
        self.assertTrue(Question.is_allowed_type(Question.LONG_TEXT))
        self.assertFalse(Question.is_allowed_type("Some Google Type"))

    def test_is_allowed_sort(self):
        self.assertTrue(Question.is_allowed_sort(Question.AUTO_SORT))
        self.assertFalse(Question.is_allowed_sort("Some Google Sort"))

    def test_num_choices(self):
        rubric = create_rubric_with_questions_and_choices()

        for question in rubric.question_set.all():
            if question.show_choices():
                self.assertIsInstance(question.num_choices_display(), int)
                self.assertEquals(question.num_choices_display(), 5)
            else:
                self.assertEquals(question.num_choices_display(), '-')

    @given(question_type=sane_text())
    def test_invalid_question_type_raises_error(self, question_type):
        rubric = create_rubric_with_questions_and_choices()
        with self.assertRaises(ValueError):
            mommy.make(Question, rubric=rubric, question_type=question_type)

    @given(sort_option=one_of(sane_text(), none()))
    def test_invalid_sort_option_raises_error(self, sort_option):
        rubric = create_rubric_with_questions_and_choices()
        with self.assertRaises(ValueError):
            mommy.make(Question, rubric=rubric, question_type=Question.LONG_TEXT,
                       choice_sort=sort_option)

    @given(fixed_decimals(min_value=0.001))
    def test_unweighted_question_type_with_non_zero_weight_raises_value_error(self, weight):
        rubric = create_rubric_with_questions_and_choices()
        with self.assertRaises(ValueError):
            mommy.make(Question, rubric=rubric, question_type=Question.LONG_TEXT,
                       weight=weight)

    @given(rubric_with_questions(min_questions=1))
    def test_add_choice(self, rubric):
        self.assertIsInstance(rubric, Rubric)
        question = rubric.question_set.first()

        def add_questions():
            question.add_choice(1, 'Low')
            question.add_choice(10, 'High')

        if question.show_choices():
            add_questions()
            self.assertQuerysetEqual(question.choice_set.order_by('description').all(),
                                     ['<Choice: High>', '<Choice: Low>'])
        else:
            with self.assertRaises(AttributeError):
                add_questions()


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

        question = q_resp.question
        if question.question_type == Question.LONG_TEXT:
            q_resp.update_response('This is some long text')
        elif question.question_type == Question.MULTI_SELECT_TYPE:
            choices = [choice[0] for choice in question.choices()]
            q_resp.update_response(choices)
        else:
            q_resp.update_response(next(question.choices()))

        self.assertTrue(rubric_response.has_response)
        self.assertTrue(q_resp.question_answered)

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


def make_rubric():
    rubric = mommy.make(Rubric, name="Test Rubric")
    default_weight = float('{0:.3f}'.format(1 / len(Question.CHOICE_TYPES)))
    for question_type in Question.available_types():
        question_is_choice_type = question_type in Question.CHOICE_TYPES
        weight = 0
        if question_is_choice_type:
            weight = default_weight
        question = mommy.make(Question,
                              rubric=rubric,
                              short_description='Question %s' % question_type,
                              long_description='This is for question %s' % question_type,
                              help_text='This is help text for question %s' % question_type,
                              weight=weight,
                              question_type=question_type,
                              required=True)
        if question_is_choice_type:
            for key in range(1, 4):
                mommy.make(Choice, question=question, order=key,
                           key=str(key), description='Choice %s' % key)
    return rubric


def make_rubric_response(rubric=None):
    if not rubric:
        rubric = make_rubric()

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

    def test_score(self):
        def check_response(response: QuestionResponse):
            q_type = response.question.question_type
            if q_type == Question.LONG_TEXT:
                with self.assertRaises(TypeError):
                    response.score()
            elif q_type == Question.MULTI_SELECT_TYPE:
                self.assertAlmostEqual(response.score(), 0.999, places=3)
            else:
                self.assertAlmostEqual(response.score(), 0.333)

        self.generic_response_test(check_response)

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



