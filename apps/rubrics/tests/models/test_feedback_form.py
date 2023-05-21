# pylint: disable=E1101


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
    Choice,
    ChoiceResponseListFeedbackModule,
    FeedbackForm,
    FeedbackModule,
    FreeTextListFeedbackModule,
    MarkdownFeedbackModule,
    Question,
    Rubric,
    RubricResponse,
    ScoreTableFeedbackModule,
)
from apps.rubrics.tests.fixtures.models import test_feedback_form as fixtures
from apps.rubrics.tests.utils import answer_rubric_response, make_rubric_response


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

    def test_create_score_table_module(self):
        module = FeedbackModule(
            feedback_form=self.feedback_form,
            order=1,
            module_type=FeedbackFormModuleType.SCORE_TABLE,
        )
        module.save()
        self.assertEqual(module, FeedbackModule.objects.first())

        score_table_module = ScoreTableFeedbackModule.objects.first()
        self.assertIsNotNone(score_table_module)
        self.assertEqual(score_table_module.feedback_form, module.feedback_form)
        self.assertEqual(score_table_module.order, module.order)
        self.assertEqual(score_table_module.module_type, module.module_type)

    def test_create_choice_response_list_module(self):
        module = FeedbackModule(
            feedback_form=self.feedback_form,
            order=1,
            module_type=FeedbackFormModuleType.CHOICE_RESPONSE_LIST,
        )
        module.save()
        self.assertEqual(module, FeedbackModule.objects.first())

        score_table_module = ChoiceResponseListFeedbackModule.objects.first()
        self.assertIsNotNone(score_table_module)
        self.assertEqual(score_table_module.feedback_form, module.feedback_form)
        self.assertEqual(score_table_module.order, module.order)
        self.assertEqual(score_table_module.module_type, module.module_type)

    def test_create_free_text_list_module(self):
        module = FeedbackModule(
            feedback_form=self.feedback_form,
            order=1,
            module_type=FeedbackFormModuleType.FREE_TEXT_LIST,
        )
        module.save()
        self.assertEqual(module, FeedbackModule.objects.first())

        score_table_module = FreeTextListFeedbackModule.objects.first()
        self.assertIsNotNone(score_table_module)
        self.assertEqual(score_table_module.feedback_form, module.feedback_form)
        self.assertEqual(score_table_module.order, module.order)
        self.assertEqual(score_table_module.module_type, module.module_type)


class FeedbackModuleTestBase(TestCase):
    MODULE = MarkdownFeedbackModule
    MODULE_TYPE = FeedbackFormModuleType.MARKDOWN

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()

        cls.rubric = make_test_rubric()
        cls.feedback_form = FeedbackForm(rubric=cls.rubric)
        cls.feedback_form.save()

    def assertHTMLEqual(self, html1: str, html2: str, msg: str | None = ...) -> None:
        try:
            return super().assertHTMLEqual(html1, html2, msg)
        except self.failureException as err:
            print(html1)
            raise err

    @classmethod
    def _add_choices(cls, question: Question):
        for key in range(1, 4):
            Choice.objects.create(
                question=question, order=key, key=str(key), description=f"Choice {key}"
            )

    @classmethod
    def _create_module(cls, **kwargs) -> MODULE:
        module = cls.MODULE(
            feedback_form=cls.feedback_form,
            order=1,
            module_type=cls.MODULE_TYPE,
            **kwargs,
        )
        module.save()
        return module

    def _test_create(self):
        module = self._create_module()
        self.assertEqual(module, self.MODULE.objects.first())

    def _test_render_html(self):
        module = self._create_module()

        make_rubric_response(self.rubric)

        self.assertIsInstance(
            module.render_html(RubricResponse.objects.all()), SafeString
        )


class MarkdownFeedbackModuleTests(FeedbackModuleTestBase):
    MODULE = MarkdownFeedbackModule
    MODULE_TYPE = FeedbackFormModuleType.MARKDOWN

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()

        cls.rubric = make_test_rubric()
        cls.feedback_form = FeedbackForm(rubric=cls.rubric)
        cls.feedback_form.save()

    @classmethod
    def _create_module(cls, **kwargs) -> MarkdownFeedbackModule:
        module = cls.MODULE(
            feedback_form=cls.feedback_form,
            order=1,
            module_type=cls.MODULE_TYPE,
            **kwargs,
        )
        module.save()
        return module

    def test_create(self):
        self._test_create()

    def test_render_html(self):
        self._test_render_html()

    def test_get_html(self):
        module = self._create_module()

        expected_html = "<h1>Heading 1</h1>\n<p>Write content here</p>"
        self.assertHTMLEqual(module.get_html(), expected_html)

    def test_average_score_with_no_responses(self):
        module = self._create_module(content="{{ average_score }}")

        make_rubric_response(self.rubric)
        make_rubric_response(self.rubric)

        expected_html = "<p></p>"
        self.assertHTMLEqual(
            module.render_html(RubricResponse.objects.all()), expected_html
        )

    def test_average_score_with_responses(self):
        module = self._create_module(content="# Average Score: {{ average_score }}")

        response1 = make_rubric_response(self.rubric)
        answer_rubric_response(response1)
        response2 = make_rubric_response(self.rubric)
        answer_rubric_response(response2)

        expected_html = "<h1>Average Score: 1.67</h1>"
        self.assertHTMLEqual(
            module.render_html(RubricResponse.objects.all()), expected_html
        )

    def test_average_score_with_partial_responses(self):
        module = self._create_module(content="# Average Score: {{ average_score }}")

        response = make_rubric_response(self.rubric)
        answer_rubric_response(response)
        make_rubric_response(self.rubric)

        expected_html = "<h1>Average Score: 1.67</h1>"
        self.assertHTMLEqual(
            module.render_html(RubricResponse.objects.all()), expected_html
        )


class ScoreTableFeedbackModuleTests(FeedbackModuleTestBase):
    MODULE = ScoreTableFeedbackModule
    MODULE_TYPE = FeedbackFormModuleType.SCORE_TABLE
    FIXTURES = fixtures.score_table_feedback_module_tests

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()

        default_weight = float(f"{1 / len(Question.CHOICE_TYPES):.3f}")

        cls.scale_question = Question.objects.create(
            rubric=cls.rubric,
            short_description="Scale Question",
            long_description="Long description for scale question",
            help_text="This is help text for scale question",
            weight=default_weight,
            question_type=Question.SCALE_TYPE,
            required=True,
        )
        cls._add_choices(cls.scale_question)

        cls.single_select_question = Question.objects.create(
            rubric=cls.rubric,
            short_description="Single-Select Question",
            long_description="Long description for single-select question",
            help_text="This is help text for single-select question",
            weight=default_weight,
            question_type=Question.SINGLE_SELECT_TYPE,
            required=True,
        )
        cls._add_choices(cls.single_select_question)

        cls.multi_select_question_numeric = Question.objects.create(
            rubric=cls.rubric,
            short_description="Multi-Select Question",
            long_description="Long description for multi-select question",
            help_text="This is help text for multi-select question",
            weight=default_weight,
            question_type=Question.MULTI_SELECT_TYPE,
            required=True,
        )
        cls._add_choices(cls.multi_select_question_numeric)

        cls.free_text = Question.objects.create(
            rubric=cls.rubric,
            short_description="Free Text Question",
            long_description="Long description for free text question",
            help_text="This is help text for free text question",
            weight=0.0,
            question_type=Question.LONG_TEXT,
            required=True,
        )

    def test_create(self):
        self._test_create()

    def test_render_html(self):
        self._test_render_html()

    def test_default_options(self):
        module = self._create_module()
        module.questions.add(
            self.scale_question,
            self.single_select_question,
            self.multi_select_question_numeric,
        )

        response = make_rubric_response(self.rubric)
        answer_rubric_response(response)

        actual_html = str(module.render_html(RubricResponse.objects.all()))
        expected_html = self.FIXTURES.test_default_options_html
        self.assertHTMLEqual(actual_html, expected_html)

    def test_no_include_short_description(self):
        module = self._create_module(include_short_description=False)
        module.questions.add(
            self.scale_question,
            self.single_select_question,
            self.multi_select_question_numeric,
        )

        response = make_rubric_response(self.rubric)
        answer_rubric_response(response)

        actual_html = str(module.render_html(RubricResponse.objects.all()))
        expected_html = self.FIXTURES.test_no_include_short_description_html
        self.assertHTMLEqual(actual_html, expected_html)

    def test_no_include_long_description(self):
        module = self._create_module(include_long_description=False)
        module.questions.add(
            self.scale_question,
            self.single_select_question,
            self.multi_select_question_numeric,
        )

        response = make_rubric_response(self.rubric)
        answer_rubric_response(response)

        actual_html = str(module.render_html(RubricResponse.objects.all()))
        expected_html = self.FIXTURES.test_no_include_long_description_html
        self.assertHTMLEqual(actual_html, expected_html)

    def test_include_titles(self):
        module = self._create_module(
            table_title="Presentation Elements",
            short_description_title="Component",
            long_description_title="Details",
            score_title="Average Score",
        )
        module.questions.add(
            self.scale_question,
            self.single_select_question,
            self.multi_select_question_numeric,
        )

        response = make_rubric_response(self.rubric)
        answer_rubric_response(response)

        actual_html = str(module.render_html(RubricResponse.objects.all()))
        expected_html = self.FIXTURES.test_include_titles_html
        self.assertHTMLEqual(actual_html, expected_html)

    def test_use_weighted_scores(self):
        module = self._create_module(use_weighted_scores=True)
        module.questions.add(
            self.scale_question,
            self.single_select_question,
            self.multi_select_question_numeric,
        )

        response = make_rubric_response(self.rubric)
        answer_rubric_response(response)

        actual_html = str(module.render_html(RubricResponse.objects.all()))
        expected_html = self.FIXTURES.test_use_weighted_scores_html
        self.assertHTMLEqual(actual_html, expected_html)

    def test_no_remove_empty_scores(self):
        module = self._create_module(remove_empty_scores=False)
        module.questions.add(
            self.scale_question,
            self.single_select_question,
            self.multi_select_question_numeric,
        )

        response = make_rubric_response(self.rubric)
        answer_rubric_response(response)

        actual_html = str(module.render_html(RubricResponse.objects.all()))
        expected_html = self.FIXTURES.test_no_remove_empty_scores_html
        self.assertHTMLEqual(actual_html, expected_html)


class ChoiceResponseListFeedbackModuleTests(FeedbackModuleTestBase):
    MODULE = ChoiceResponseListFeedbackModule
    MODULE_TYPE = FeedbackFormModuleType.CHOICE_RESPONSE_LIST
    FIXTURES = fixtures.choice_response_list_feedback_module_tests

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()

        default_weight = float(f"{1 / len(Question.CHOICE_TYPES):.3f}")

        cls.scale_question = Question.objects.create(
            rubric=cls.rubric,
            short_description="Scale Question",
            long_description="Long description for scale question",
            help_text="This is help text for scale question",
            weight=default_weight,
            question_type=Question.SCALE_TYPE,
            required=True,
        )
        cls._add_choices(cls.scale_question)

        cls.single_select_question = Question.objects.create(
            rubric=cls.rubric,
            short_description="Single-Select Question",
            long_description="Long description for single-select question",
            help_text="This is help text for single-select question",
            weight=default_weight,
            question_type=Question.SINGLE_SELECT_TYPE,
            required=True,
        )
        cls._add_choices(cls.single_select_question)

        cls.multi_select_question_numeric = Question.objects.create(
            rubric=cls.rubric,
            short_description="Multi-Select Question",
            long_description="Long description for multi-select question",
            help_text="This is help text for multi-select question",
            weight=default_weight,
            question_type=Question.MULTI_SELECT_TYPE,
            required=True,
        )
        cls._add_choices(cls.multi_select_question_numeric)

        cls.free_text = Question.objects.create(
            rubric=cls.rubric,
            short_description="Free Text Question",
            long_description="Long description for free text question",
            help_text="This is help text for free text question",
            weight=0.0,
            question_type=Question.LONG_TEXT,
            required=True,
        )

    def test_create(self):
        self._test_create()

    def test_render_html(self):
        self._test_render_html()

    def test_default_options(self):
        module = self._create_module()

        response = make_rubric_response(self.rubric)
        answer_rubric_response(response)

        actual_html = str(module.render_html(RubricResponse.objects.all()))
        expected_html = self.FIXTURES.test_default_options_html
        self.assertHTMLEqual(actual_html, expected_html)

    def test_with_single_select_question(self):
        module = self._create_module(question=self.single_select_question)

        response = make_rubric_response(self.rubric)
        answer_rubric_response(response)

        actual_html = str(module.render_html(RubricResponse.objects.all()))
        expected_html = self.FIXTURES.test_with_single_select_question_html
        self.assertHTMLEqual(actual_html, expected_html)

    def test_with_scale_question(self):
        module = self._create_module(question=self.scale_question)

        response = make_rubric_response(self.rubric)
        answer_rubric_response(response)

        actual_html = str(module.render_html(RubricResponse.objects.all()))
        expected_html = self.FIXTURES.test_with_single_select_question_html
        self.assertHTMLEqual(actual_html, expected_html)

    def test_with_multi_select_question(self):
        module = self._create_module(question=self.multi_select_question_numeric)

        response = make_rubric_response(self.rubric)
        answer_rubric_response(response)

        actual_html = str(module.render_html(RubricResponse.objects.all()))
        expected_html = self.FIXTURES.test_with_multi_select_question_html
        self.assertHTMLEqual(actual_html, expected_html)

    def test_with_multiple_responses(self):
        module = self._create_module(question=self.multi_select_question_numeric)

        response = make_rubric_response(self.rubric)
        answer_rubric_response(response)

        response = make_rubric_response(self.rubric)
        answer_rubric_response(response)

        actual_html = str(module.render_html(RubricResponse.objects.all()))
        expected_html = self.FIXTURES.test_with_multi_select_question_html
        self.assertHTMLEqual(actual_html, expected_html)

    def test_no_remove_duplicates(self):
        module = self._create_module(
            question=self.multi_select_question_numeric, remove_duplicates=False
        )

        response = make_rubric_response(self.rubric)
        answer_rubric_response(response)

        response = make_rubric_response(self.rubric)
        answer_rubric_response(response)

        actual_html = str(module.render_html(RubricResponse.objects.all()))
        expected_html = self.FIXTURES.test_no_remove_duplicates_html
        self.assertHTMLEqual(actual_html, expected_html)

    def test_no_display_description(self):
        module = self._create_module(
            question=self.multi_select_question_numeric, display_description=False
        )

        response = make_rubric_response(self.rubric)
        answer_rubric_response(response)

        actual_html = str(module.render_html(RubricResponse.objects.all()))
        expected_html = self.FIXTURES.test_no_display_description_html
        self.assertHTMLEqual(actual_html, expected_html)


class FreeTextListFeedbackModuleTests(FeedbackModuleTestBase):
    MODULE = FreeTextListFeedbackModule
    MODULE_TYPE = FeedbackFormModuleType.FREE_TEXT_LIST
    FIXTURES = fixtures.free_text_list_feedback_module_tests

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()

        cls.free_text = Question.objects.create(
            rubric=cls.rubric,
            short_description="Free Text Question",
            long_description="Long description for free text question",
            help_text="This is help text for free text question",
            weight=0.0,
            question_type=Question.LONG_TEXT,
            required=True,
        )

    def test_create(self):
        self._test_create()

    def test_render_html(self):
        self._test_render_html()

    def test_default_options(self):
        module = self._create_module()

        response = make_rubric_response(self.rubric)
        answer_rubric_response(response)

        actual_html = str(module.render_html(RubricResponse.objects.all()))
        expected_html = self.FIXTURES.test_default_options_html
        self.assertHTMLEqual(actual_html, expected_html)

    def test_with_question(self):
        module = self._create_module(question=self.free_text)

        response = make_rubric_response(self.rubric)
        answer_rubric_response(response)

        actual_html = str(module.render_html(RubricResponse.objects.all()))
        expected_html = self.FIXTURES.test_with_question_html
        self.assertHTMLEqual(actual_html, expected_html)

    def test_no_responses(self):
        module = self._create_module(question=self.free_text)

        make_rubric_response(self.rubric)

        actual_html = str(module.render_html(RubricResponse.objects.all()))
        expected_html = self.FIXTURES.test_no_responses_html
        self.assertHTMLEqual(actual_html, expected_html)

    def test_multiple_responses(self):
        module = self._create_module(question=self.free_text)

        response = make_rubric_response(self.rubric)
        question_response = response.questionresponse_set.get(question=self.free_text)
        question_response.update_response(
            "This response is from the first rubric response."
        )

        response = make_rubric_response(self.rubric)
        question_response = response.questionresponse_set.get(question=self.free_text)
        question_response.update_response("And this response is from the second one.")

        actual_html = str(module.render_html(RubricResponse.objects.all()))
        expected_html = self.FIXTURES.test_multiple_responses_html
        self.assertHTMLEqual(actual_html, expected_html)
