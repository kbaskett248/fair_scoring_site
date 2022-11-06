from typing import Iterator

from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Count, QuerySet
from django.db.models.signals import post_save
from django.dispatch import receiver

from fair_projects.models import JudgingInstance, Project
from judges.models import Judge
from rubrics.models import Rubric

from .logic import (
    get_judging_rubric,
    get_num_judges_per_project,
    get_num_projects_per_judge,
)


def add_instances(
    queryset: QuerySet, minimum_instances: int, other_min: int, **kwargs
) -> None:
    rubric = get_judging_rubric()
    for instance in AssignmentHelper.get_instances_for(queryset, **kwargs):
        if not instance.exists(rubric):
            instance.assign(rubric)

            if AssignmentHelper.instance_count(rubric, **kwargs) < minimum_instances:
                continue

            other_count = AssignmentHelper.instance_count(
                rubric, **instance.other_kwarg(**kwargs)
            )
            if other_count > other_min:
                break


def remove_nonmatching_instances(**kwargs) -> Iterator["ExistingInstanceHelper"]:
    """Remove Judging Instances that no longer match and aren't locked."""
    rubric = get_judging_rubric()
    for instance in ExistingInstanceHelper.get_instances_for(
        rubric=rubric, locked=False, **kwargs
    ):
        if not instance.attributes_match():
            instance.remove()
            yield instance


def add_judges_to_project(project: Project) -> None:
    available_judges = Judge.objects.filter(
        user__is_active=True, categories=project.category, divisions=project.division
    )
    add_instances(
        available_judges,
        get_num_judges_per_project(),
        get_num_projects_per_judge(),
        project=project,
    )


def add_projects_to_judge(judge: Judge) -> None:
    if judge.user.is_active:
        categories = list(judge.categories.values_list("pk", flat=True))
        divisions = list(judge.divisions.values_list("pk", flat=True))
        available_projects = Project.objects.filter(
            category__in=categories, division__in=divisions
        )
        add_instances(
            available_projects,
            get_num_projects_per_judge(),
            get_num_judges_per_project(),
            judge=judge,
        )


def remove_excess_instances() -> None:
    """Remove unlocked Judging Instances until below the limits.

    Get the JudgingInstance objects where the number of projects for the
    judge and the number of judges for the project exceed the limit. If there
    are any, remove the first and then requery.

    """
    rubric = get_judging_rubric()
    queryset = (
        JudgingInstance.objects.filter(response__rubric=rubric, locked=False)
        .annotate(
            num_projects=Count("judge__judginginstance", distinct=True),
            num_judges=Count("project__judginginstance", distinct=True),
        )
        .filter(
            num_projects__gt=get_num_projects_per_judge(),
            num_judges__gt=get_num_judges_per_project(),
        )
        .order_by("num_judges", "num_projects")
        .reverse()
        .select_related("response")
    )

    # Result needs to be a list so we can pop the first item
    def get_instances():
        return list(queryset.all())

    instances = get_instances()

    while instances:
        instance = instances.pop()
        instance.delete()
        if instances:
            instances = get_instances()


@receiver(
    post_save, sender=Project, dispatch_uid="update_judging_instances_for_project"
)
def update_judging_instances_for_project(
    sender: type, instance: Project, **kwargs
) -> None:
    # Remove non-matching judges and any judges that are no longer active
    deleted_instances = list(remove_nonmatching_instances(project=instance))
    judges_to_update = {i.judge for i in deleted_instances}

    add_judges_to_project(instance)
    for judge in judges_to_update:
        add_projects_to_judge(judge)
    remove_excess_instances()


@receiver(
    Judge.post_commit, sender=Judge, dispatch_uid="update_judging_instances_for_judge"
)
def update_judging_instances_for_judge(sender: type, instance: Judge, **kwargs) -> None:
    # Remove nonmatching projects
    deleted_instances = list(remove_nonmatching_instances(judge=instance))
    projects_to_update = {i.project for i in deleted_instances}

    add_projects_to_judge(instance)
    for project in projects_to_update:
        add_judges_to_project(project)
    remove_excess_instances()


@receiver(
    post_save, sender=User, dispatch_uid="update_judging_instances_for_inactive_judges"
)
def update_judging_instances_for_inactive_judges(
    sender: type, instance: User, **kwargs
) -> None:
    if not instance.is_active:
        try:
            judge = Judge.objects.get(pk=instance.pk)
        except ObjectDoesNotExist:
            pass
        else:
            deleted_instances = list(remove_nonmatching_instances(judge=judge))
            projects_to_update = {i.project for i in deleted_instances}
            for project in projects_to_update:
                add_judges_to_project(project)
            remove_excess_instances()


class AssignmentHelper:
    @classmethod
    def get_instances_for(cls, queryset, **kwargs) -> Iterator["AssignmentHelper"]:
        queryset = queryset.annotate(num_existing=Count("judginginstance")).order_by(
            "num_existing"
        )
        for item in queryset.all():
            kw_args = {"project": item, "judge": item}
            kw_args.update(kwargs)
            yield cls(**kw_args)

    def __init__(self, project, judge):
        self.project = project
        self.judge = judge

    def assign(self, rubric: Rubric) -> JudgingInstance:
        return JudgingInstance.objects.create(
            judge=self.judge, project=self.project, rubric=rubric
        )

    def exists(self, rubric: Rubric) -> bool:
        return JudgingInstance.objects.filter(
            judge=self.judge, project=self.project, response__rubric=rubric.pk
        ).exists()

    def kwargs(self) -> dict:
        return {"project": self.project, "judge": self.judge}

    def other_kwarg(self, **kwargs) -> dict:
        d = self.kwargs()
        for k in kwargs.keys():
            d.pop(k, None)
        return d

    @staticmethod
    def instance_count(rubric: Rubric, **kwargs):
        return JudgingInstance.objects.filter(
            response__rubric=rubric.pk, **kwargs
        ).count()


class ExistingInstanceHelper:
    @classmethod
    def get_instances_for(cls, **kwargs) -> Iterator["ExistingInstanceHelper"]:
        rubric = kwargs.pop("rubric", None)
        if rubric:
            kwargs["response__rubric"] = rubric
        queryset = (
            JudgingInstance.objects.filter(**kwargs)
            .select_related(
                "judge",
                "project",
                "project__category",
                "project__division",
                "judge__user",
            )
            .prefetch_related("judge__categories", "judge__divisions")
        )
        for judging_instance in queryset.all():
            yield cls(judging_instance)

    def __init__(self, judging_instance: JudgingInstance):
        self.judging_instance = judging_instance

    @property
    def judge(self) -> Judge:
        return self.judging_instance.judge

    @property
    def project(self) -> Project:
        return self.judging_instance.project

    @property
    def locked(self) -> bool:
        return self.judging_instance.locked

    def remove(self):
        self.judging_instance.delete()

    def attributes_match(self) -> bool:
        return (
            self.judge.user.is_active
            and (self.project.category in self.judge.categories.all())
            and (self.project.division in self.judge.divisions.all())
        )
