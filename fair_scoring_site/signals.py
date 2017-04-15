from django.db.models.signals import post_save
from django.dispatch import receiver

from .logic import get_judging_rubric
from fair_projects.models import Project, JudgingInstance
from judges.models import Judge


def update_instances(sender: type, **kwargs):
    rubric = get_judging_rubric()
    AssignmentHelper = assignment_helper_factory(sender)
    for judge in AssignmentHelper.get_instances_for(**kwargs):
        judge.assign(rubric)


@receiver(post_save, sender=Project, dispatch_uid='update_judging_instances_for_project')
def update_judging_instances_for_project(sender: type, instance: Project, **kwargs) -> None:
    update_instances(sender, project=instance)


@receiver(post_save, sender=Judge, dispatch_uid='update_judging_instances_for_judge')
def update_judging_instances_for_judge(sender: type, instance: Judge, **kwargs) -> None:
    update_instances(sender, judge=instance)
        
        
class AssignmentHelperBase:
    @classmethod
    def get_instances_for(cls, **kwargs):
        queryset = cls._get_queryset(**kwargs)
        for item in queryset.all():
            kw_args = {'project': item, 'judge': item}
            kw_args.update(kwargs)
            yield cls(**kw_args)

    def __init__(self, project, judge):
        self.project = project
        self.judge = judge

    def assign(self, rubric):
        return JudgingInstance.objects.create(judge=self.judge,
                                              project=self.project,
                                              rubric=rubric)


def assignment_helper_factory(obj_type: type) -> type:
    if obj_type == Project:
        class AssignmentHelper(AssignmentHelperBase):
            @classmethod
            def _get_queryset(cls, **kwargs):
                project = kwargs['project']
                return Judge.objects.filter(user__is_active=True,
                                            categories=project.category,
                                            divisions=project.division)

    elif obj_type == Judge:
        class AssignmentHelper(AssignmentHelperBase):
            @classmethod
            def _get_queryset(cls, **kwargs):
                judge = kwargs['judge']
                categories = list(judge.categories.values_list('pk', flat=True))
                divisions = list(judge.divisions.values_list('pk', flat=True))
                return Project.objects.filter(category__in=categories,
                                              division__in=divisions)

    return AssignmentHelper

