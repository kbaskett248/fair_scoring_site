from constance import config
from django.core.exceptions import ObjectDoesNotExist

from rubrics.models import Rubric


def get_judging_rubric():
    try:
        return Rubric.objects.get(name=config.RUBRIC_NAME)
    except ObjectDoesNotExist:
        return None