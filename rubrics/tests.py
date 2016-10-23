from hypothesis import given
from hypothesis import settings
from hypothesis.extra.django import TestCase as HypTestCase
from hypothesis.extra.django.models import models
from hypothesis.searchstrategy import SearchStrategy
from hypothesis.strategies import one_of, sampled_from, text, lists, integers, \
    just, tuples
from model_mommy import mommy

from rubrics.models import Rubric, Question, Choice, RubricResponse


def fixed_decimals() -> SearchStrategy:
    return integers(min_value=0, max_value=999).map(lambda x: x / 1000)


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
                self.assertIsInstance(question.num_choices(), int)
                self.assertEquals(question.num_choices(), 5)
            else:
                self.assertEquals(question.num_choices(), '-')

    @given(rubric_with_questions(min_questions=1))
    @settings(max_examples=50)
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
            q_resp.update_response(question.choices()[0])

        self.assertTrue(rubric_response.has_response)
        self.assertTrue(q_resp.question_answered)

