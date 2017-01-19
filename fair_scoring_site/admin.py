from django.contrib import admin
from django.contrib import messages
from django.contrib.contenttypes.admin import GenericTabularInline
from django.contrib.contenttypes.forms import BaseGenericInlineFormSet
from django.core.exceptions import ValidationError
from django.urls.base import reverse
from django.utils.html import format_html
from django.utils.translation import gettext as _

import awards.admin
import fair_projects
from awards.logic import InstanceBase, assign_awards
from awards.models import Award, AwardInstance
from fair_projects.logic import get_projects_sorted_by_score
from fair_projects.models import Project


admin.site.unregister(Project)
admin.site.unregister(Award)
admin.site.unregister(AwardInstance)


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
        self.grade_level = self.calculate_grade_level()

        self.awards.extend(Award.get_awards_for_object(self.project))

    def __str__(self):
        return self.project.__str__()

    def calculate_grade_level(self):
        return max((student.grade_level for student in self.project.student_set.all()), default=None)


class AwardRuleForm(awards.admin.AwardRuleForm):
    traits = ('category',
              'subcategory',
              'division',
              'number',
              'grade_level')


class AwardRuleInline(awards.admin.AwardRuleInline):
    form = AwardRuleForm


class AwardInstanceInline(awards.admin.AwardInstanceInline):
    readonly_fields = ('project_number', 'project_title', 'project_students', 'project_category', 'project_division')

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

    def project_category(self, instance):
        return instance.content_object.category

    def project_division(self, instance):
        return instance.content_object.division

    def view_on_site(self, instance):
        return reverse('fair_projects:detail', args=(instance.content_object.number, ))


class TraitListFilter(awards.admin.TraitListFilter):
    award_rule_form_class = AwardRuleForm


@admin.register(Award)
class AwardAdmin(awards.admin.AwardAdmin):
    actions = (assign_awards_to_projects, )
    inlines = (AwardRuleInline, AwardInstanceInline)
    list_filter = (TraitListFilter, )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


@admin.register(AwardInstance)
class AwardInstanceAdmin(awards.admin.AwardInstanceAdmin):
    list_filter = ('award', TraitListFilter)
    list_display = ('award', 'project', 'students', 'category', 'division')
    fields = ('award', 'project', 'students', 'category', 'division')
    readonly_fields = ('award', 'project', 'students', 'category', 'division')

    def project(self, instance):
        return instance.content_object

    def students(self, instance):
        return ', '.join(str(student) for student in
                         instance.content_object.student_set.all())

    def category(self, instance):
        return instance.content_object.category

    def division(self, instance):
        return instance.content_object.division


class ProjectAwardFormset(BaseGenericInlineFormSet):
    model = AwardInstance

    def clean(self):
        super(ProjectAwardFormset, self).clean()

        project_instance = ProjectInstance(self.instance)
        for form in self.forms:
            if not form.cleaned_data:
                continue
            elif form.cleaned_data['DELETE']:
                continue
            self.clean_award(project_instance, form.cleaned_data['award'])

    def clean_award(self, instance, award):
        if not award.instance_passes_all_rules(instance):
            raise ValidationError(
                _('%(award)s is not valid for this project'),
                code='invalid award for project',
                params={'award': award}
            )
        elif award.exclude_from_instance(instance):
            raise ValidationError(
                _('Cannot assign %(award)s to this project due to excluded awards'),
                code='excluded award for project',
                params={'award': award}
            )


class ProjectAwardInline(GenericTabularInline):
    model = AwardInstance
    formset = ProjectAwardFormset


@admin.register(Project)
class ProjectAdmin(fair_projects.admin.ProjectAdmin):
    inlines = (fair_projects.admin.StudentInline,
               fair_projects.admin.JudgingInstanceInline,
               ProjectAwardInline)
