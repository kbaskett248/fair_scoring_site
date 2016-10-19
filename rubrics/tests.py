from django.test import TestCase

from rubrics.models import Rubric, Question, Choice


def create_simple_rubric():
    rubric = Rubric.objects.create(name="Simple Rubric")
    question = rubric.add_question(Question.SCALE_TYPE,
                                  'Scale Question',
                                  weight=1.0)
    question.add_choice(1, 'Low'),
    question.add_choice(10, 'High')
    return rubric


class RubricTests(TestCase):
    def test_add_question(self):
        create_simple_rubric()
        self.assertQuerysetEqual(Rubric.objects.all(), ['<Rubric: Simple Rubric>'])


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


