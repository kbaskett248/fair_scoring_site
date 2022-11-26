from django.core.exceptions import ValidationError
from django.test import TestCase
from hypothesis import given
from hypothesis.extra.django import TestCase as HypTestCase
from hypothesis.extra.django import from_model

from apps.rubrics.constants import FeedbackFormModuleType
from apps.rubrics.fixtures import make_test_rubric
from apps.rubrics.models.feedback_form import (
    FeedbackForm,
    FeedbackModule,
    MarkdownFeedbackModule,
)
from apps.rubrics.models.rubric import Rubric


class FeedbackFormTests(HypTestCase):
    @given(from_model(Rubric))
    def test_create(self, rubric: Rubric):
        feedback_form = FeedbackForm(rubric=rubric)
        self.assertIn(rubric.name, str(feedback_form))


class FeedbackModuleTests(TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()

        cls.rubric = make_test_rubric()
        cls.feedback_form = FeedbackForm(rubric=cls.rubric)
        cls.feedback_form.save()

    def test_create(self):
        module = FeedbackModule(
            feedback_form=self.feedback_form,
            order=1,
            module_type=FeedbackFormModuleType.MARKDOWN,
        )
        module.save()
        self.assertEqual(module, FeedbackModule.objects.first())

    def test_cannot_create_with_missing_order(self):
        with self.assertRaises(ValidationError):
            module = FeedbackModule(
                feedback_form=self.feedback_form,
                module_type=FeedbackFormModuleType.MARKDOWN,
            )
            module.save()

    def test_cannot_create_with_missing_module_type(self):
        with self.assertRaises(ValidationError):
            module = FeedbackModule(
                feedback_form=self.feedback_form,
                order=1,
            )
            module.save()

    def test_create_markdown_module(self):
        module = FeedbackModule(
            feedback_form=self.feedback_form,
            order=1,
            module_type=FeedbackFormModuleType.MARKDOWN,
        )
        module.save()
        self.assertEqual(module, FeedbackModule.objects.first())

        markdown_module = MarkdownFeedbackModule.objects.first()
        self.assertIsNotNone(markdown_module)
        self.assertEqual(markdown_module.feedback_form, module.feedback_form)
        self.assertEqual(markdown_module.order, module.order)
        self.assertEqual(markdown_module.module_type, module.module_type)


class MarkdownFeedbackModuleTests(TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()

        cls.rubric = make_test_rubric()
        cls.feedback_form = FeedbackForm(rubric=cls.rubric)
        cls.feedback_form.save()

    def test_create(self):
        module = MarkdownFeedbackModule(
            feedback_form=self.feedback_form,
            order=1,
            module_type=FeedbackFormModuleType.MARKDOWN,
        )
        module.save()
        self.assertEqual(module, MarkdownFeedbackModule.objects.first())

    def test_get_html(self):
        module = MarkdownFeedbackModule(
            feedback_form=self.feedback_form,
            order=1,
            module_type=FeedbackFormModuleType.MARKDOWN,
        )
        module.save()

        expected_html = "<h1>Heading 1</h1>\n<p>Write content here</p>\n"
        self.assertEqual(module.get_html(), expected_html)
