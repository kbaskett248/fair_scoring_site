from functools import reduce

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from .models import Question, Choice, QuestionResponse, RubricResponse, Rubric


@receiver(post_save, sender=Question)
def createRelatedQuestionResponses(sender: type, instance: Question, created: bool, **kwargs) -> None:
    """When saving a question, make sure there is a QuestionResponse for all RubricResponse objects

    New QuestionResponse instances are created using bulk_create. This doesn't
    call save and doesn't trigger pre_save or post_save hooks.

    Arguments:
        sender: The model class sending this signal. Should be Question.
        instance: The Question instance that was saved.
        created: True if the instance was created.
        **kwargs: Additional, unused keyword arguments.

    """
    question_id = instance
    rubric_id = instance.rubric_id

    all_rubric_responses = get_rubric_response_set(rubric_id)
    rubric_responses_for_specified_question = get_rubric_response_set_related_to_question(question_id)

    new_responses = []
    for rr in all_rubric_responses - rubric_responses_for_specified_question:
        new_responses.append(QuestionResponse(rubric_response_id=rr, question=question_id))

    QuestionResponse.objects.bulk_create(new_responses)


def get_rubric_response_set(rubric_id) -> set:
    queryset = RubricResponse.objects\
               .filter(rubric_id=rubric_id)\
               .values_list('id', flat=True)
    return set(queryset)

def get_rubric_response_set_related_to_question(question_id) -> set:
    queryset = QuestionResponse.objects\
               .filter(question_id=question_id)\
               .values_list('rubric_response_id', flat=True)
    return set(queryset)


@receiver(post_delete, sender=Question)
def deleteRelatedQuestionResponses(sender: type, instance: Question, **kwargs) -> None:
    """When deleting a question, delete the associated QuestionResponse objects.

    Arguments:
        sender: The model class sending this signal. Should be Question.
        instance: The Question instance that was saved.
        **kwargs: Additional, unused keyword arguments.

    """
    pass

@receiver(post_save, sender=Choice)
@receiver(post_delete, sender=Choice)
def deleteResponsesForChoice(sender: type, instance: Choice, **kwargs) -> None:
    """When saving or deletting a Choice, delete the response from all associated
    QuestionResponse objects.

    Arguments:
        sender: The model class sending this signal. Should be Question.
        instance: The Question instance that was saved.
        **kwargs: Additional, unused keyword arguments.

    """
    pass
