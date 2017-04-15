from django.db.models.signals import post_save
from django.dispatch import receiver

from .logic import get_judging_rubric
from fair_projects.models import Project, JudgingInstance
from judges.models import Judge


def update_instances(queryset, **kwargs):
    rubric = get_judging_rubric()
    for judge in AssignmentHelper.get_instances_for(queryset, **kwargs):
        judge.assign(rubric)


@receiver(post_save, sender=Project, dispatch_uid='update_judging_instances_for_project')
def update_judging_instances_for_project(sender: type, instance: Project, **kwargs) -> None:
    queryset = Judge.objects.filter(user__is_active=True,
                                    categories=instance.category,
                                    divisions=instance.division)
    update_instances(queryset, project=instance)


@receiver(post_save, sender=Judge, dispatch_uid='update_judging_instances_for_judge')
def update_judging_instances_for_judge(sender: type, instance: Judge, **kwargs) -> None:
    categories = list(instance.categories.values_list('pk', flat=True))
    divisions = list(instance.divisions.values_list('pk', flat=True))
    queryset = Project.objects.filter(category__in=categories,
                                      division__in=divisions)
    update_instances(queryset, judge=instance)
        
        
class AssignmentHelper:
    @classmethod
    def get_instances_for(cls, queryset, **kwargs):
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

