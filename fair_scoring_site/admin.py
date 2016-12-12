from django.contrib import admin
from django.contrib import messages

import awards.admin
from awards import InstanceBase, assign_awards
from awards.models import Award
from fair_projects.logic import get_projects_sorted_by_score


def assign_awards_to_projects(modeladmin, request, queryset):
    instances = [ProjectInstance(project) for project in get_projects_sorted_by_score()]
    assign_awards(queryset, instances)
    for instance in instances:
        if instance.awards:
            messages.add_message(request, messages.INFO,
                                 'Assigned {0} to {1}'.format(instance.awards_str, instance.project))
    messages.add_message(request, messages.INFO, 'Awards assigned')

assign_awards_to_projects.short_description = 'Assign selected awards to projects'


class ProjectInstance(InstanceBase):
    def __init__(self, project):
        super().__init__()
        self.project = project
        self.category = self.project.category
        self.subcategory = self.project.subcategory
        self.division = self.project.division
        self.number = self.project.number

    def __str__(self):
        return self.project.__str__()


class AwardRuleForm(awards.admin.AwardRuleForm):
    traits = ('category',
              'subcategory',
              'division',
              'number')


class AwardRuleInline(awards.admin.AwardRuleInline):
    form = AwardRuleForm


class AwardAdmin(awards.admin.AwardAdmin):
    actions = (assign_awards_to_projects, )
    inlines = (AwardRuleInline,)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


admin.site.register(Award, admin_class=AwardAdmin)
