import unittest
from collections.abc import Callable
from contextlib import contextmanager
from datetime import datetime

from django.utils import timezone
from hypothesis import given
from hypothesis.extra.django import TestCase as HypTestCase
from model_bakery import baker

from apps.rubrics.fixtures import make_test_rubric
from apps.rubrics.models.rubric import (
    Choice,
    Question,
    QuestionResponse,
    Rubric,
    RubricResponse,
)
from apps.rubrics.tests.strategies import question_type_st
from apps.rubrics.tests.utils import (
    answer_rubric_response,
    create_rubric_with_questions_and_choices,
    make_rubric_response,
)


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

        for q_resp in rubric_response.questionresponse_set.filter(
            question__required=True
        ):
            self.answer_question(q_resp)

        self.assertTrue(rubric_response.complete)

    @staticmethod
    def answer_question(question_resp):
        question = question_resp.question
        if question.question_type == Question.LONG_TEXT:
            question_resp.update_response("This is some long text")
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

        self.assertEqual(
            rub_response.score(), 0, "Score is not zero before answering the Rubric"
        )

        answer_rubric_response(rub_response)

        self.assertAlmostEqual(
            rub_response.score(), 1.665, 3, "Score incorrect after answering the Rubric"
        )


class QuestionResponseTests(HypTestCase):
    def test_empty_responses(self):
        rub_response = make_rubric_response()
        for response in rub_response.questionresponse_set.select_related(
            "question"
        ).all():
            if response.question.question_type == Question.MULTI_SELECT_TYPE:
                self.assertEqual(
                    response.response,
                    [],
                    (
                        f"Empty response not equal to {[]} "
                        f"for question type {response.question.question_type}"
                    ),
                )
            else:
                self.assertEqual(
                    response.response,
                    None,
                    (
                        f"Empty response not equal to {None} "
                        f"for question type {response.question.question_type}"
                    ),
                )

    def test_empty_responses_external(self):
        rub_response = make_rubric_response()
        for response in rub_response.questionresponse_set.select_related(
            "question"
        ).all():
            if response.question.question_type == Question.MULTI_SELECT_TYPE:
                self.assertEqual(
                    response.response_external(),
                    [],
                    (
                        f"Empty external response not equal to {[]} "
                        f"for question type {response.question.question_type}"
                    ),
                )
            else:
                self.assertEqual(
                    response.response_external(),
                    None,
                    (
                        f"Empty external response not equal to {None} "
                        f"for question type {response.question.question_type}"
                    ),
                )

    def generic_response_test(self, check_response: Callable):
        rub_response = make_rubric_response()
        answer_rubric_response(rub_response)

        for response in rub_response.questionresponse_set.select_related(
            "question"
        ).all():
            check_response(response)

    def test_response(self):
        value_dict = {
            Question.LONG_TEXT: "This is a long text response.\nThis is a second line",
            Question.MULTI_SELECT_TYPE: ["1", "2"],
            "default": "1",
        }

        def check_response(response: QuestionResponse):
            value = value_dict.get(
                response.question.question_type, value_dict["default"]
            )
            self.assertEqual(
                response.response,
                value,
                (
                    f"Response not equal to {value} "
                    f"for question type {response.question.question_type}"
                ),
            )

        self.generic_response_test(check_response)

    def test_response_external(self):
        value_dict = {
            Question.LONG_TEXT: "This is a long text response.\nThis is a second line",
            Question.MULTI_SELECT_TYPE: ["Choice 1", "Choice 2"],
            "default": "Choice 1",
        }

        def check_response(response: QuestionResponse):
            value = value_dict.get(
                response.question.question_type, value_dict["default"]
            )
            self.assertEqual(
                response.response_external(),
                value,
                (
                    f"Response not equal to {value} "
                    f"for question type {response.question.question_type}"
                ),
            )

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

    # Choice was updated so that non-numeric choices could not be saved for
    # weighted questions.
    @unittest.expectedFailure
    def test_score_for_non_numeric_choices(self):
        rubric = baker.make(Rubric, name="Test Rubric")
        rub_response = make_rubric_response(rubric)

        question_type = Question.SINGLE_SELECT_TYPE
        question = baker.make(
            Question,
            rubric=rubric,
            short_description=f"Question {question_type}",
            long_description=f"This is for question {question_type}",
            help_text=f"This is help text for question {question_type}",
            weight=1,
            question_type=question_type,
            required=True,
        )
        choices = baker.make(Choice, _quantity=4, question=question)
        q_resp = baker.make(
            QuestionResponse, rubric_response=rub_response, question=question
        )
        q_resp.update_response(choices[0].key)
        self.assertEqual(
            q_resp.score(),
            0,
            msg="Score should be zero for questions with non-numeric choices",
        )

        question_type = Question.MULTI_SELECT_TYPE
        question = baker.make(
            Question,
            rubric=rubric,
            short_description=f"Question {question_type}",
            long_description=f"This is for question {question_type}",
            help_text=f"This is help text for question {question_type}",
            weight=1,
            question_type=question_type,
            required=True,
        )
        choices = baker.make(Choice, _quantity=4, question=question)
        q_resp = baker.make(
            QuestionResponse, rubric_response=rub_response, question=question
        )
        q_resp.update_response([choices[0].key, choices[1].key])
        self.assertEqual(
            q_resp.score(),
            0,
            msg="Score should be zero for questions with non-numeric choices",
        )

    def test_last_saved_date(self):
        rub_response = make_rubric_response()

        for response in rub_response.questionresponse_set.select_related(
            "question"
        ).all():
            self.assertIsNone(response.last_submitted)

        answer_rubric_response(rub_response)
        now = timezone.now()

        for response in rub_response.questionresponse_set.select_related(
            "question"
        ).all():
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
        rub_response = make_rubric_response()

        question: Question = baker.make(
            Question,
            rubric=rub_response.rubric,
            short_description="Additional test question",
        )

        self.assertTrue(
            rub_response.questionresponse_set.filter(
                question__short_description="Additional test question"
            ).exists()
        )

        response = rub_response.questionresponse_set.get(
            question__short_description="Additional test question"
        )
        self.assertEqual(question, response.question)

    def test_deleted_question_is_removed_from_response(self):
        rub_response = make_rubric_response()
        num_question_responses = rub_response.questionresponse_set.count()

        question = rub_response.questionresponse_set.first().question

        question.delete()
        self.assertEqual(
            rub_response.questionresponse_set.count(), num_question_responses - 1
        )
        self.assertQuerysetEqual(
            rub_response.questionresponse_set.all(),
            [
                "Test Rubric: Question SINGLE SELECT",
                "Test Rubric: Question MULTI SELECT",
                "Test Rubric: Question LONG TEXT",
            ],
            transform=lambda x: str(x.question),
            ordered=False,
        )


class QuestionResponseClearingTests(HypTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.rubric = make_test_rubric()

    def setUp(self):
        super().setUp()
        self.rub_response = make_rubric_response(self.rubric)
        answer_rubric_response(self.rub_response)

    def get_question_and_response(
        self, question_type: str
    ) -> tuple[Question, QuestionResponse]:
        question = self.rub_response.rubric.question_set.filter(
            question_type=question_type
        ).first()
        response = self.rub_response.questionresponse_set.get(question_id=question.id)

        self.assertTrue(response.question_answered)

        return question, response

    def get_choice_and_response(
        self, question_type: str
    ) -> tuple[Choice, QuestionResponse]:
        question, response = self.get_question_and_response(question_type)
        choice = question.choice_set.first()
        return choice, response

    @staticmethod
    def update_question_type(question: Question, new_type: str) -> None:
        question.question_type = new_type
        question.save()

    @staticmethod
    def refresh_response(response: QuestionResponse) -> QuestionResponse:
        # Refreshing the response since refresh_from_db doesn't seem to work
        return QuestionResponse.objects.get(id=response.id)

    @contextmanager
    def assert_only_response_for_choice_cleared(self, question_type: str):
        choice, response = self.get_choice_and_response(question_type)
        yield choice
        self.assert_only_given_response_cleared(response)

    def assert_only_given_response_cleared(self, response: QuestionResponse) -> None:
        for resp in self.rub_response.questionresponse_set.all():
            if resp.pk == response.pk:
                self.assertFalse(resp.question_answered)
            else:
                self.assertTrue(resp.question_answered)

    def assert_no_responses_cleared(self):
        for resp in self.rub_response.questionresponse_set.all():
            self.assertTrue(resp.question_answered)

    @given(question_type_st())
    def test_clear_responses_when_question_type_changed(self, new_type):
        question, response = self.get_question_and_response(Question.LONG_TEXT)
        self.update_question_type(question, new_type)

        if new_type == Question.LONG_TEXT:
            self.assert_no_responses_cleared()
        else:
            self.assert_only_given_response_cleared(response)

    def test_responses_are_not_cleared_for_special_case(self):
        # Scale type and Single select type are the same with different widgets,
        # so nothing is cleared in this special case.
        for starting_type, new_type in (
            (Question.SCALE_TYPE, Question.SINGLE_SELECT_TYPE),
            (Question.SINGLE_SELECT_TYPE, Question.SCALE_TYPE),
        ):
            with self.subTest(f"{starting_type} -> {new_type}"):
                question, _ = self.get_question_and_response(starting_type)
                self.update_question_type(question, new_type)
                self.assert_no_responses_cleared()

    @given(question_type_st().filter(lambda x: x in Question.CHOICE_TYPES))
    def test_clear_responses_when_choice_changes(self, question_type):
        with self.assert_only_response_for_choice_cleared(question_type) as choice:
            choice.key = 10000
            choice.save()

    @given(question_type_st().filter(lambda x: x in Question.CHOICE_TYPES))
    def test_clear_responses_when_choice_deleted(self, question_type):
        with self.assert_only_response_for_choice_cleared(question_type) as choice:
            choice.delete()

    @given(question_type_st().filter(lambda x: x in Question.CHOICE_TYPES))
    def test_clear_responses_when_choice_added(self, question_type):
        with self.assert_only_response_for_choice_cleared(question_type) as choice:
            baker.make(Choice, question=choice.question, key=10000)
