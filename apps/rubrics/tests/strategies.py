from typing import Optional

from hypothesis.extra.django import from_model
from hypothesis.strategies import (
    SearchStrategy,
    integers,
    just,
    lists,
    one_of,
    sampled_from,
    text,
    tuples,
)

from apps.rubrics.models import Question, Rubric


def fixed_decimals(
    min_value: float = 0, max_value: float = 1, num_decimals=3
) -> SearchStrategy:
    power_of_ten = 10**num_decimals
    return integers(
        min_value=(min_value * power_of_ten), max_value=(max_value * power_of_ten)
    ).map(lambda x: x / power_of_ten)


def sane_text(min_size=0, max_size=1024) -> SearchStrategy:
    return text(
        alphabet=[chr(i) for i in range(33, 126)],
        min_size=min_size,
        max_size=max_size,
    )


def question_type_st() -> SearchStrategy:
    return sampled_from(Question.CHOICE_TYPES)


def question_type_and_weight() -> SearchStrategy:
    return one_of(
        tuples(sampled_from(Question.CHOICE_TYPES), fixed_decimals()),
        tuples(
            sampled_from(
                sorted(set(Question.available_types()) - set(Question.CHOICE_TYPES))
            ),
            just(0),
        ),
    )


def questions(rubric: Rubric) -> SearchStrategy:
    def create_question(type_and_weight: tuple) -> SearchStrategy:
        return from_model(
            Question,
            rubric=just(rubric),
            question_type=just(type_and_weight[0]),
            weight=just(type_and_weight[1]),
            short_description=sane_text(),
        )

    return question_type_and_weight().flatmap(create_question)


def rubric_with_questions(
    min_questions: int = 0, max_questions: Optional[int] = None
) -> SearchStrategy:
    def add_questions(rubric: Rubric) -> SearchStrategy:
        return lists(
            elements=questions(rubric),
            min_size=min_questions,
            max_size=max_questions,
            unique=True,
        ).flatmap(lambda _: just(rubric))

    return from_model(Rubric).flatmap(add_questions)
