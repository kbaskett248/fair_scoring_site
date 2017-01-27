from django.core.management.base import BaseCommand
from django.db import transaction

from rubrics.models import QuestionResponse, Question, Choice


@transaction.atomic
def fix_scores():
    scale_type_dict = {'Far Below': '1',
                       'Fair': '2',
                       'Average': '3',
                       'Good': '4',
                       'Excellent': '5'}

    qr_queryset = QuestionResponse.objects.select_related('question') \
        .filter(question__question_type=Question.SCALE_TYPE)

    for question_response in qr_queryset.all():
        from_ = question_response.choice_response
        if from_ is None:
            continue
        to_ = scale_type_dict[question_response.choice_response]
        print("changing response from %s to %s" % (from_, to_))
        question_response.choice_response = scale_type_dict[question_response.choice_response]
        question_response.save()

    choice_queryset = Choice.objects.filter(question__question_type=Question.SCALE_TYPE)

    for choice in choice_queryset.all():
        from_ = choice.key
        to_ = scale_type_dict[choice.key]
        print("changing key from %s to %s" % (from_, to_))
        choice.key = scale_type_dict[choice.key]
        choice.save()


class Command(BaseCommand):
    help = 'Fixes the scores'


    def handle(self, *args, **options):
        fix_scores()
