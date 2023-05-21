import random

from model_bakery import baker

from apps.rubrics.fixtures import make_test_rubric
from apps.rubrics.models import Choice, Question, Rubric, RubricResponse


def create_rubric_with_questions_and_choices() -> Rubric:
    rubric = baker.make(Rubric)
    for _ in range(0, 10):
        required = bool(random.getrandbits(1))
        question = baker.make(Question, rubric=rubric, required=required)
        if question.show_choices():
            for _ in range(0, 5):
                baker.make(Choice, question=question)

    return rubric


def make_rubric_response(rubric=None) -> RubricResponse:
    rubric = rubric or make_test_rubric()

    return baker.make(RubricResponse, rubric=rubric)


def answer_rubric_response(rubric_response):
    for q_resp in rubric_response.questionresponse_set.all():
        if q_resp.question.question_type == Question.MULTI_SELECT_TYPE:
            q_resp.update_response(["1", "2"])
        elif q_resp.question.question_type == Question.LONG_TEXT:
            q_resp.update_response(
                "This is a long text response.\nThis is a second line"
            )
        else:
            q_resp.update_response("1")
