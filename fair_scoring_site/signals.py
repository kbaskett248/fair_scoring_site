from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.db.models.signals import post_save
from django.dispatch import receiver

from rubrics.models import Rubric
from .logic import get_judging_rubric
from fair_projects.models import Project, JudgingInstance
from judges.models import Judge


def add_instances(queryset, **kwargs):
    rubric = get_judging_rubric()
    for instance in AssignmentHelper.get_instances_for(queryset, **kwargs):
        if not instance.exists(rubric):
            instance.assign(rubric)


def remove_nonmatching_instances(**kwargs):
    rubric = get_judging_rubric()
    for instance in ExistingInstanceHelper.get_instances_for(rubric=rubric, **kwargs):
        if not instance.attributes_match():
            instance.remove()


@receiver(post_save, sender=Project, dispatch_uid='update_judging_instances_for_project')
def update_judging_instances_for_project(sender: type, instance: Project, **kwargs) -> None:
    # Remove non-matching judges and any judges that are no longer active
    remove_nonmatching_instances(project=instance)

    judges_to_add = Judge.objects.filter(user__is_active=True,
                                         categories=instance.category,
                                         divisions=instance.division)
    add_instances(judges_to_add, project=instance)


@receiver(post_save, sender=Judge, dispatch_uid='update_judging_instances_for_judge')
def update_judging_instances_for_judge(sender: type, instance: Judge, **kwargs) -> None:
    # Remove nonmatching projects
    remove_nonmatching_instances(judge=instance)

    if instance.user.is_active:
        categories = list(instance.categories.values_list('pk', flat=True))
        divisions = list(instance.divisions.values_list('pk', flat=True))
        projects_to_add = Project.objects.filter(category__in=categories,
                                                 division__in=divisions)
        add_instances(projects_to_add, judge=instance)


@receiver(post_save, sender=User, dispatch_uid='update_judging_instances_for_inactive_judges')
def update_judging_instances_for_inactive_judges(sender: type, instance: User, **kwargs) -> None:
    if not instance.is_active:
        try:
            judge = Judge.objects.get(pk=instance.pk)
        except ObjectDoesNotExist:
            pass
        else:
            remove_nonmatching_instances(judge=judge)
        
        
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

    def assign(self, rubric: Rubric) -> JudgingInstance:
        return JudgingInstance.objects.create(judge=self.judge,
                                              project=self.project,
                                              rubric=rubric)

    def exists(self, rubric: Rubric) -> bool:
        return JudgingInstance.objects.filter(judge=self.judge,
                                              project=self.project,
                                              response__rubric=rubric.pk)


class ExistingInstanceHelper:
    @classmethod
    def get_instances_for(cls, **kwargs):
        rubric = kwargs.pop('rubric', None)
        if rubric:
            kwargs['response__rubric'] = rubric
        queryset = JudgingInstance.objects\
                                  .filter(**kwargs)\
                                  .select_related('judge', 'project', 'project__category',
                                                  'project__division', 'judge__user')\
                                  .prefetch_related('judge__categories', 'judge__divisions')
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

    def remove(self):
        self.judging_instance.delete()

    def attributes_match(self) -> bool:
        return (self.judge.user.is_active and
                (self.project.category in self.judge.categories.all()) and
                (self.project.division in self.judge.divisions.all()))
