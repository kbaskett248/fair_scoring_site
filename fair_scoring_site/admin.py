from django.contrib import admin
from django.contrib import messages
from django.contrib.contenttypes.admin import GenericTabularInline
from django.urls.base import reverse
from django.utils.html import format_html

import awards.admin
import fair_projects
from awards.logic import InstanceBase, assign_awards
from awards.models import Award, AwardInstance
from fair_projects.logic import get_projects_sorted_by_score
from fair_projects.models import Project


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
    model_attr = 'project'

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


class AwardInstanceInline(awards.admin.AwardInstanceInline):
    readonly_fields = ('project_number', 'project_title', 'project_students')

    def admin_link(self, instance, text):
        return format_html(
            '<a href="{0}">{1}</a>',
            reverse('admin:fair_projects_project_change', args=(instance.content_object.pk,)),
            text
        )

    def project_title(self, instance):
        return self.admin_link(instance, instance.content_object.title)

    def project_number(self, instance):
        return self.admin_link(instance, instance.content_object.number)

    def project_students(self, instance):
        return ', '.join(str(student) for student in
                         instance.content_object.student_set.all())

    def view_on_site(self, instance):
        return reverse('fair_projects:detail', args=(instance.content_object.number, ))


@admin.register(Award)
class AwardAdmin(awards.admin.AwardAdmin):
    actions = (assign_awards_to_projects, )
    inlines = (AwardRuleInline, AwardInstanceInline)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


@admin.register(AwardInstance)
class AwardInstanceAdmin(admin.ModelAdmin):
    model = AwardInstance
    list_display = ('award', 'content_object')


class ProjectAwardInline(GenericTabularInline):
    model = AwardInstance


admin.site.unregister(Project)


@admin.register(Project)
class ProjectAdmin(fair_projects.admin.ProjectAdmin):
    inlines = (fair_projects.admin.StudentInline, ProjectAwardInline)
