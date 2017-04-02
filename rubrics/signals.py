from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from .models import Question, Choice, QuestionResponse

@receiver(post_save, sender=Question)
def createRelatedQuestionResponses(sender: type, instance: Question, created: bool, **kwargs) -> None:
    """When saving a question, make sure there is a QuestionResponse for all RubricResponse objects

    Arguments:
        sender: The model class sending this signal. Should be Question.
        instance: The Question instance that was saved.
        created: True if the instance was created.
        **kwargs: Additional, unused keyword arguments.

    """
    pass

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
