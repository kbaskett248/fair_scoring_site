from model_mommy import mommy

from rubrics.models import Rubric, Question, Choice


def make_test_rubric(name: str = "Test Rubric") -> Rubric:
    rubric = mommy.make(Rubric, name=name)
    default_weight = float("{0:.3f}".format(1 / len(Question.CHOICE_TYPES)))
    for question_type in Question.available_types():
        question_is_choice_type = question_type in Question.CHOICE_TYPES
        weight = 0.0
        if question_is_choice_type:
            weight = default_weight
        question = mommy.make(
            Question,
            rubric=rubric,
            short_description="Question %s" % question_type,
            long_description="This is for question %s" % question_type,
            help_text="This is help text for question %s" % question_type,
            weight=weight,
            question_type=question_type,
            required=True,
        )
        if question_is_choice_type:
            for key in range(1, 4):
                mommy.make(
                    Choice,
                    question=question,
                    order=key,
                    key=str(key),
                    description="Choice %s" % key,
                )
    return rubric
