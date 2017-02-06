import types

import functools

from functools import singledispatch, reduce
from itertools import groupby, permutations, product

from django.contrib import admin
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.contenttypes.admin import GenericTabularInline
from django.contrib.contenttypes.forms import BaseGenericInlineFormSet
from django.core.exceptions import ValidationError
from django.db.models.base import Model
from django.db.models.query import QuerySet
from django.urls.base import reverse
from django.utils.html import format_html
from django.utils.translation import gettext as _
from import_export import resources, fields
from import_export.admin import ExportMixin, ImportExportMixin
from import_export.widgets import ForeignKeyWidget, CharWidget

import awards.admin
import fair_projects
from awards.logic import InstanceBase, assign_awards
from awards.models import Award, AwardInstance
from fair_categories.models import Category, Subcategory, Division, Ethnicity
from fair_projects.logic import get_projects_sorted_by_score
from fair_projects.models import Project, Student

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


class AwardInstanceResource(resources.ModelResource):
    award = fields.Field()
    project = fields.Field()
    students = fields.Field()
    category = fields.Field()
    division = fields.Field()

    class Meta:
        model = AwardInstance
        fields = ('award', 'project', 'students', 'category', 'division')
        export_order = ('award', 'project', 'students', 'category', 'division')

    def dehydrate_award(self, instance):
        return instance.award.name

    def dehydrate_project(self, instance):
        return instance.content_object.title

    def dehydrate_students(self, instance):
        return instance.content_object.student_str()

    def dehydrate_category(self, instance):
        return instance.content_object.category

    def dehydrate_division(self, instance):
        return instance.content_object.division


def convert_field_name_to_column_name(field_name: str) -> str:
    return field_name.replace("_", " ").title()


@singledispatch
def tuplify(_object):
    return _object, _object


@tuplify.register(tuple)
def _(_object):
    return _object


@tuplify.register(list)
@tuplify.register(set)
def _(_object):
    return tuple(_object)


class StudentResource(resources.ModelResource):
    class Meta:
        model = Student
        fields = ('number', 'title', 'category', 'subcategory', 'division',
                  'first_name', 'last_name', 'gender', 'ethnicity', 'grade_level', 'teacher', 'email')
        export_order = fields
        import_id_fields = ('first_name', 'last_name')

    number = fields.Field(attribute='project', column_name='Number',
                          widget=ForeignKeyWidget(Project, 'number'))

    title = fields.Field(attribute='project', column_name='Title',
                         widget=ForeignKeyWidget(Project, 'title'))

    category = fields.Field(attribute='project__category', column_name='Category',
                            widget=ForeignKeyWidget(Category, 'short_description'))

    subcategory = fields.Field(attribute='project__subcategory', column_name='Subcategory',
                               widget=ForeignKeyWidget(Subcategory, 'short_description'))

    division = fields.Field(attribute='project__division', column_name='Division',
                            widget=ForeignKeyWidget(Division, 'short_description'))

    first_name = fields.Field(attribute='first_name', column_name='Student First Name')
    last_name = fields.Field(attribute='last_name', column_name='Student Last Name')
    gender = fields.Field(attribute='gender', column_name='Student Gender')
    grade_level = fields.Field(attribute='grade_level', column_name='Student Grade Level')
    email = fields.Field(attribute='email', column_name='Student Email')
    ethnicity = fields.Field(attribute='ethnicity', column_name='Ethnicity',
                             widget=ForeignKeyWidget(Ethnicity, 'short_description'))
    teacher = fields.Field(attribute='teacher__user', column_name='Teacher',
                           widget=ForeignKeyWidget(User, 'last_name'))

    def export(self, queryset=None, *args, **kwargs):
        if queryset:
            project_keys = [values['pk'] for values in queryset.values('pk')]
            queryset = Student.objects.filter(project__in=project_keys)
        else:
            queryset = Student.objects.all()

        queryset = queryset.select_related('project', 'ethnicity').order_by('project__number')

        return super(StudentResource, self).export(queryset, *args, **kwargs)

    def before_import_row(self, row, **kwargs):
        pass

    def after_import_row(self, row, row_result, **kwargs):
        pass


class ProjectResource(resources.ModelResource):
    category = fields.Field(attribute='category',
                            column_name='category',
                            widget=ForeignKeyWidget(Category, 'short_description'))
    subcategory = fields.Field(attribute='subcategory',
                               column_name='subcategory',
                               widget=ForeignKeyWidget(Subcategory, 'short_description'))
    division = fields.Field(attribute='division',
                            column_name='division',
                            widget=ForeignKeyWidget(Division, 'short_description'))

    class Meta:
        model = Project
        fields = ('number', 'title', 'category', 'subcategory', 'division')
        export_order = ('number', 'title', 'category', 'subcategory', 'division')
        import_id_fields = ('title', 'number')


class AwardRuleForm(awards.admin.AwardRuleForm):
    traits = ('category',
              'subcategory',
              'division',
              'number',
              'grade_level')

    def generic_validation(self, model: Model, key: str, fields: dict):
        for value in self.individual_value_iterator(**fields):
            filters = {key: value}
            if not model.objects.filter(**filters).exists():
                params = fields.copy()
                params['value'] = value
                self.raise_default_validation_error(params)

    def validate_category(self, **fields):
        self.generic_validation(Category, 'short_description', fields)

    def validate_subcategory(self, **fields):
        self.generic_validation(Subcategory, 'short_description', fields)

    def validate_division(self, **fields):
        self.generic_validation(Division, 'short_description', fields)

    def validate_number(self, **fields):
        self.generic_validation(Project, 'number', fields)

    def validate_grade_level(self, **fields):
        for value in self.individual_value_iterator(**fields):
            if not value.isdecimal() or not 1 <= int(value) <= 12:
                params = fields.copy()
                params['value'] = value
                raise ValidationError('Values for the %(trait)s trait must be numbers between 1 and 12',
                                      code='invalid trait value',
                                      params=params)


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
        return instance.content_object.student_str()

    def project_category(self, instance):
        return instance.content_object.category

    def project_division(self, instance):
        return instance.content_object.division

    def view_on_site(self, instance):
        return reverse('fair_projects:detail', args=(instance.content_object.number,))


class TraitListFilter(awards.admin.TraitListFilter):
    award_rule_form_class = AwardRuleForm


@admin.register(Award)
class AwardAdmin(awards.admin.AwardAdmin):
    actions = (assign_awards_to_projects,)
    inlines = (AwardRuleInline, AwardInstanceInline)
    list_filter = (TraitListFilter,)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


@admin.register(AwardInstance)
class AwardInstanceAdmin(ExportMixin, awards.admin.AwardInstanceAdmin):
    list_filter = ('award', TraitListFilter)
    list_display = ('award', 'project', 'students', 'category', 'division')
    fields = ('award', 'project', 'students', 'category', 'division')
    readonly_fields = ('award', 'project', 'students', 'category', 'division')

    resource_class = AwardInstanceResource

    def project(self, instance):
        return instance.content_object

    def students(self, instance):
        return instance.content_object.student_str()

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
class ProjectAdmin(ImportExportMixin, fair_projects.admin.ProjectAdmin):
    inlines = (fair_projects.admin.StudentInline,
               fair_projects.admin.JudgingInstanceInline,
               ProjectAwardInline)

    resource_class = ProjectResource
