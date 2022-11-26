from hypothesis import given
from hypothesis.extra.django import TestCase as HypTestCase
from hypothesis.extra.django import from_model

from apps.rubrics.models.feedback_form import FeedbackForm
from apps.rubrics.models.rubric import Rubric


class FeedbackFormTests(HypTestCase):
    @given(from_model(Rubric))
    def test_create(self, rubric: Rubric):
        feedback_form = FeedbackForm(rubric=rubric)
        self.assertIn(rubric.name, str(feedback_form))
