from constance import config
from django.core.exceptions import ObjectDoesNotExist

from rubrics.models import Rubric


def get_judging_rubric_name() -> str:
    return config.RUBRIC_NAME


def get_judging_rubric() -> Rubric:
    try:
        return Rubric.objects.get(name=get_judging_rubric_name())
    except ObjectDoesNotExist:
        return None
