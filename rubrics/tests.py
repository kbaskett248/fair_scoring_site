from django.test import TestCase
from hypothesis import given
from hypothesis import settings
from hypothesis.extra.django import TestCase as HypTestCase
from hypothesis.extra.django.models import models
from hypothesis.strategies import one_of, sampled_from, text, lists, fixed_dictionaries, integers, \
    booleans, none

from rubrics.models import Rubric, Question, Choice


def create_simple_rubric():
    rubric = Rubric.objects.create(name="Simple Rubric")
    question = rubric.add_question(Question.SCALE_TYPE,
                                   'Scale Question',
                                   weight=1.0)
    question.add_choice(1, 'Low'),
    question.add_choice(10, 'High')
    return rubric


def and_none(strategy):
    return one_of(strategy, none())


def remove_none_values(dictionary: dict):
    for key, value in dictionary.copy().items():
        if value is None:
            del dictionary[key]
    return dictionary


add_question_dictionaries = fixed_dictionaries(
    {'question_type': sampled_from(Question.available_types()),
     'short_description': text(),
     'weight': and_none(integers(min_value=0, max_value=9999).map(lambda x: x / 1000)),
     'order': and_none(integers(min_value=0, max_value=1000)),
     'long_description': and_none(text()),
     'help_text': and_none(text()),
     'choice_sort': and_none(sampled_from(Question.sort_options())),
     'required': and_none(booleans())
     }).map(remove_none_values)


class RubricTests(HypTestCase):
    @given(text())
    def test_create_rubric(self, name):
        rubric = Rubric.objects.create(name=name)
        self.assertEqual(rubric.name, name)
        self.assertQuerysetEqual(Rubric.objects.all(), ['<Rubric: %s>' % name])

    @given(models(Rubric),
           lists(add_question_dictionaries, min_size=0, max_size=20))
    @settings(max_examples=50)
    def test_add_question(self, rubric: Rubric, questions):
        question_list = []
        for question in questions:
            q_type = question.pop('question_type')
            short_description = question.pop('short_description')
            if question.get('choice_sort', False) and (q_type not in Question.CHOICE_TYPES):
                with self.assertRaises(ValueError):
                    rubric.add_question(q_type, short_description, **question)
            else:
                question = rubric.add_question(q_type, short_description, **question)
                retrieved_question = Question.objects.get(short_description=short_description)

                self.assertIsNotNone(question)
                self.assertEqual(question, retrieved_question)
                question_list.append('<Question: %s>' % short_description)

        question_list.sort()
        self.assertQuerysetEqual(Question.objects.order_by('short_description').all(),
                                 question_list)
        self.assertQuerysetEqual(rubric.question_set.order_by('short_description').all(),
                                 question_list)


class QuestionTests(TestCase):
    def test_is_allowed_type(self):
        self.assertTrue(Question.is_allowed_type(Question.LONG_TEXT))
        self.assertFalse(Question.is_allowed_type("Some Google Type"))

    def test_is_allowed_sort(self):
        self.assertTrue(Question.is_allowed_sort(Question.AUTO_SORT))
        self.assertFalse(Question.is_allowed_sort("Some Google Sort"))

    def test_add_choice(self):
        rubric = create_simple_rubric()
        qs = Choice.objects.order_by('description')
        self.assertQuerysetEqual(qs.all(),
                                 ['<Choice: High>', '<Choice: Low>'])
        self.assertQuerysetEqual(qs.filter(question__rubric=rubric).all(),
                                 ['<Choice: High>', '<Choice: Low>'],
                                 ordered=True)
        self.assertQuerysetEqual(qs.filter(question__short_description='Scale Question').all(),
                                 ['<Choice: High>', '<Choice: Low>'],
                                 ordered=True)


class RubricResponseTests(TestCase):
    pass
