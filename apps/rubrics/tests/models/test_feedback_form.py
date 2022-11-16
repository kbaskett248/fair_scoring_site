from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils.safestring import SafeString
from hypothesis import given
from hypothesis import strategies as st
from hypothesis.extra.django import TestCase as HypTestCase
from hypothesis.extra.django import from_model

from apps.rubrics.constants import FeedbackFormModuleType
from apps.rubrics.fixtures import make_test_rubric
from apps.rubrics.models import (
    FeedbackForm,
    FeedbackModule,
    MarkdownFeedbackModule,
    Rubric,
    RubricResponse,
)
from apps.rubrics.tests.tests import make_rubric_response


class FeedbackFormTests(HypTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.rubric = make_test_rubric()
        cls.rubric_response = make_rubric_response(cls.rubric)

    @given(from_model(Rubric))
    def test_create(self, rubric: Rubric):
        feedback_form = FeedbackForm(rubric=rubric)
        self.assertIn(rubric.name, str(feedback_form))

    def test_render_html(self):
        feedback_form = FeedbackForm(rubric=self.rubric)
        feedback_form.save()

        module = MarkdownFeedbackModule(
            feedback_form=feedback_form,
            order=1,
            module_type=FeedbackFormModuleType.MARKDOWN,
        )
        module.save()

        rendered_html = feedback_form.render_html(RubricResponse.objects.all())

        self.assertIsInstance(rendered_html, SafeString)


class FeedbackFormManagerTests(HypTestCase):
    @given(st.sets(from_model(Rubric), min_size=0, max_size=10))
    def test_for_rubric_responses(self, rubrics: set[Rubric]):
        responses = {make_rubric_response(rubric) for rubric in rubrics}
        response_ids = {response.id for response in responses}

        expected_forms = {
            FeedbackForm.objects.create(rubric=rubric) for rubric in rubrics
        }
        response_queryset = RubricResponse.objects.filter(id__in=response_ids)

        actual_forms = set(FeedbackForm.objects.for_rubric_responses(response_queryset))

        self.assertEqual(expected_forms, actual_forms)

    @given(st.sets(from_model(Rubric), min_size=0, max_size=10))
    def test_render_html_responses(self, rubrics: set[Rubric]):
        responses = {make_rubric_response(rubric) for rubric in rubrics}
        response_ids = {response.id for response in responses}

        expected_forms = {
            FeedbackForm.objects.create(rubric=rubric) for rubric in rubrics
        }
        response_queryset = RubricResponse.objects.filter(id__in=response_ids)

        feedback_contexts = list(
            FeedbackForm.objects.render_html_for_responses(response_queryset)
        )

        actual_forms = set()
        for context in feedback_contexts:
            self.assertIsInstance(context, FeedbackForm.FeedbackFormContext)
            actual_forms.add(context.form)
            self.assertIsInstance(context.html, SafeString)

        self.assertEqual(expected_forms, actual_forms)


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

    def test_render_html(self):
        module = MarkdownFeedbackModule(
            feedback_form=self.feedback_form,
            order=1,
            module_type=FeedbackFormModuleType.MARKDOWN,
        )
        module.save()

        make_rubric_response(self.rubric)

        self.assertIsInstance(
            module.render_html(RubricResponse.objects.all()), SafeString
        )
