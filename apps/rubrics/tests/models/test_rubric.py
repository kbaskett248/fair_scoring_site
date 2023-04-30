from django.core.exceptions import ValidationError
from hypothesis import given
from hypothesis.extra.django import TestCase as HypTestCase
from hypothesis.strategies import none, one_of
from model_bakery import baker

from apps.rubrics.models.rubric import Choice, Question, Rubric, value_is_numeric
from apps.rubrics.tests.base import TestBase
from apps.rubrics.tests.strategies import (
    fixed_decimals,
    question_type_and_weight,
    sane_text,
)
from apps.rubrics.tests.utils import create_rubric_with_questions_and_choices


class RubricTests(HypTestCase):
    @given(sane_text(min_size=1))
    def test_create_rubric(self, name: str):
        rubric = Rubric.objects.create(name=name)
        self.assertEqual(rubric.name, name)
        self.assertQuerysetEqual(
            Rubric.objects.all(), [f"<Rubric: {name}>"], transform=repr
        )

    def test_create_rubric_fails_for_empty_name(self):
        with self.assertRaises(ValidationError):
            Rubric.objects.create(name="")
        self.assertQuerysetEqual(Rubric.objects.all(), [])


class QuestionTests(HypTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.rubric = create_rubric_with_questions_and_choices()

    def test_is_allowed_type(self):
        self.assertTrue(Question.is_allowed_type(Question.LONG_TEXT))
        self.assertFalse(Question.is_allowed_type("Some Google Type"))

    def test_is_allowed_sort(self):
        self.assertTrue(Question.is_allowed_sort(Question.AUTO_SORT))
        self.assertFalse(Question.is_allowed_sort("Some Google Sort"))

    def test_num_choices(self):
        for number, question in enumerate(self.rubric.question_set.all(), start=1):
            with self.subTest("Question %(number)s", number=number):
                if question.show_choices():
                    self.assertIsInstance(question.num_choices_display(), int)
                    self.assertEqual(question.num_choices_display(), 5)
                else:
                    self.assertEqual(question.num_choices_display(), "-")

    @given(question_type=sane_text())
    def test_invalid_question_type_raises_error(self, question_type):
        with self.assertRaises(ValidationError):
            baker.make(Question, rubric=self.rubric, question_type=question_type)

    @given(
        sort_option=one_of(sane_text().filter(lambda x: x not in {"A", "M"}), none())
    )
    def test_invalid_sort_option_raises_error(self, sort_option):
        with self.assertRaises(
            ValidationError,
            msg=f"No error raised for sort_option {sort_option}",
        ):
            baker.make(
                Question,
                rubric=self.rubric,
                question_type=Question.LONG_TEXT,
                choice_sort=sort_option,
            )

    @given(fixed_decimals(min_value=0.001))
    def test_unweighted_question_type_with_non_zero_weight_raises_value_error(
        self, weight
    ):
        with self.assertRaises(ValidationError):
            baker.make(
                Question,
                rubric=self.rubric,
                question_type=Question.LONG_TEXT,
                weight=weight,
            )

    def test_add_choice(self):
        def add_choices(question):
            question.add_choice(1, "Low")
            question.add_choice(10, "High")

        with self.subTest("%(type)s question", type=Question.SCALE_TYPE):
            question = baker.make(
                Question, question_type=Question.SCALE_TYPE, rubric=self.rubric
            )
            add_choices(question)
            self.assertQuerysetEqual(
                question.choice_set.order_by("description").all(),
                ["<Choice: High>", "<Choice: Low>"],
                transform=repr,
            )

        with self.subTest("%(type)s question", type=Question.LONG_TEXT):
            question = baker.make(
                Question, question_type=Question.LONG_TEXT, rubric=self.rubric
            )
            with self.assertRaises(ValidationError):
                add_choices(question)

    @given(question_type_and_weight(), question_type_and_weight())
    def test_question_type_changed(
        self, quest1: tuple[str, float], quest2: tuple[str, float]
    ):
        question = baker.make(
            Question, question_type=quest1[0], weight=0
        )  # type: Question
        self.assertEqual(question.question_type, quest1[0])
        question.question_type = quest2[0]
        self.assertEqual(question.question_type, quest2[0])

        if quest1[0] == quest2[0]:
            self.assertFalse(question.question_type_changed())
        else:
            self.assertTrue(question.question_type_changed())

    @given(question_type_and_weight(), question_type_and_weight())
    def test_question_type_changed_compatibility(
        self, quest1: tuple[str, float], quest2: tuple[str, float]
    ):
        compatible_types = (Question.SCALE_TYPE, Question.SINGLE_SELECT_TYPE)
        question = baker.make(
            Question, question_type=quest1[0], weight=0
        )  # type: Question
        self.assertEqual(question.question_type, quest1[0])
        question.question_type = quest2[0]
        self.assertEqual(question.question_type, quest2[0])

        if quest1[0] == quest2[0]:
            self.assertFalse(question.question_type_changed_compatibility())
        elif (quest1[0] in compatible_types) and (quest2[0] in compatible_types):
            self.assertFalse(question.question_type_changed_compatibility())
        else:
            self.assertTrue(question.question_type_changed_compatibility())


class ChoiceTests(TestBase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.question = baker.make(Question)  # type: Question

    def choice_test_with_positive_weight(self, key):
        self.question.weight = 1.000
        kwargs = {
            "question": self.question,
            "order": 1,
            "key": key,
            "description": "description",
        }
        if not value_is_numeric(key):
            with self.assertRaises(ValidationError):
                Choice.validate(**kwargs)
            choice = Choice(**kwargs)
            with self.assertRaises(ValidationError):
                choice.save()
        else:
            with self.assertNoException(ValidationError):
                Choice.validate(
                    question=self.question, order=1, key=key, description="description"
                )
            choice = Choice(**kwargs)
            with self.assertNoException(ValidationError):
                choice.save()

    def choice_test_with_zero_weight(self, key):
        self.question.weight = 0
        kwargs = {
            "question": self.question,
            "order": 1,
            "key": key,
            "description": "description",
        }
        with self.assertNoException(ValidationError):
            Choice.validate(**kwargs)
        choice = Choice(**kwargs)
        with self.assertNoException(ValidationError):
            choice.save()

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
        kwargs = {
            "question": self.question,
            "order": 1,
            "key": "key",
            "description": "description",
        }
        with self.assertRaises(ValidationError):
            Choice.validate(**kwargs)
        choice = Choice(**kwargs)
        with self.assertRaises(ValidationError):
            choice.save()
