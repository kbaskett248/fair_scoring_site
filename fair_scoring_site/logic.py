from constance import config
from django.core.exceptions import ObjectDoesNotExist

from apps.rubrics.models.rubric import Rubric


def get_judging_rubric_name() -> str:
    return config.RUBRIC_NAME


def get_num_judges_per_project() -> int:
    return config.JUDGES_PER_PROJECT


def get_num_projects_per_judge() -> int:
    return config.PROJECTS_PER_JUDGE


def get_judging_rubric() -> Rubric:
    try:
        return Rubric.objects.get(name=get_judging_rubric_name())
    except ObjectDoesNotExist:
        return None
