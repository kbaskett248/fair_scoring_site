from django.db.models.signals import post_save
from django.dispatch import receiver

from fair_projects.models import Project


@receiver(sender=Project, dispatch_uid='update_judging_instances_for_project')
def update_judging_instances_for_project(sender, **kwargs):
    pass