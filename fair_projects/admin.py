import django.contrib.auth.admin
from django import forms
from django.contrib import admin
from django.contrib import messages
from django.contrib.auth.tokens import default_token_generator
from django.contrib.sites.shortcuts import get_current_site
from django.db import transaction
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from import_export import resources, fields
from import_export.admin import ExportMixin, ImportExportMixin
from import_export.widgets import ForeignKeyWidget, CharWidget

from fair_categories.models import Category, Subcategory, Division, Ethnicity
from fair_projects.logic import mass_email
from fair_projects.models import JudgingInstance
from fair_scoring_site.logic import get_judging_rubric
from rubrics.models import RubricResponse
from .models import School, Teacher, Student, Project


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


class StudentResource(resources.ModelResource):
    class Meta:
        model = Student
        fields = ('first_name', 'last_name', 'gender', 'ethnicity',
                  'grade_level', 'email', 'teacher', 'project_number', 'project_title')
        export_order = ('first_name', 'last_name', 'gender', 'ethnicity',
                        'grade_level', 'email', 'teacher', 'project_number', 'project_title')
        import_id_fields = ('first_name', 'last_name')

    ethnicity = fields.Field(attribute='ethnicity',
                             column_name='ethnicity',
                             widget=ForeignKeyWidget(Ethnicity, 'short_description'))
    teacher = fields.Field(attribute='teacher__user',
                           column_name='teacher',
                           widget=ForeignKeyWidget(Teacher, 'last_name'),
                           readonly=True)
    project_number = fields.Field(attribute='project',
                                  column_name='project number',
                                  widget=ForeignKeyWidget(Project, 'number'))
    project_title = fields.Field(attribute='project',
                                 column_name='project title',
                                 widget=ForeignKeyWidget(Project, 'title'),
                                 readonly=True)


class StudentInline(admin.StackedInline):
    model = Student
    min_num = 1
    extra = 1


class JudgingInstanceForm(forms.ModelForm):
    class Meta:
        model = JudgingInstance
        fields = ('judge', )

    @transaction.atomic()
    def save(self, commit=True):
        instance = super(JudgingInstanceForm, self).save(commit=False)
        response = RubricResponse.objects.create(rubric=get_judging_rubric())
        instance.response = response
        if commit:
            instance.save()
        return instance


class JudgingInstanceInline(admin.TabularInline):
    model = JudgingInstance
    form = JudgingInstanceForm
    fields = ('judge', 'rubric', 'score')
    readonly_fields = ('rubric', 'score')

    def rubric(self, instance):
        return instance.response.rubric


@admin.register(Project)
class ProjectAdmin(ImportExportMixin, admin.ModelAdmin):
    model = Project
    list_display = ('number', 'title', 'category', 'subcategory', 'division')
    list_display_links = ('number', 'title')
    list_filter = ('category', 'division')
    ordering = ('number', 'title')
    inlines = (StudentInline, JudgingInstanceInline)
    view_on_site = True
    save_on_top = True

    resource_class = ProjectResource


@admin.register(Student)
class StudentAdmin(ImportExportMixin, admin.ModelAdmin):
    model = Student
    list_display = ('full_name', 'teacher', 'grade_level', 'project_title')
    list_filter = ('teacher', 'grade_level', 'project__category', 'project__division')
    ordering = ('last_name', 'first_name')

    resource_class = StudentResource

    def full_name(self, obj):
        return obj.full_name
    full_name.admin_order_field = 'last_name'

    def project_title(self, obj):
        try:
            return obj.project.title
        except AttributeError:
            return "-"

class TeacherInline(admin.StackedInline):
    model = Teacher
    can_delete = False
    max_num = 1
    verbose_name_plural = 'Teacher Information'

    @classmethod
    def condition(cls, request, obj=None):
        return obj and obj.has_perm('fair_projects.is_teacher')


django.contrib.auth.admin.UserAdmin.register_conditional_inline(TeacherInline)


def send_password_reset(modeladmin, request, queryset):
    current_site = get_current_site(request)
    site_name = current_site.name
    domain = current_site.domain

    targets = []
    for user in queryset:
        context = {
            'domain': domain,
            'site_name': site_name,
            'protocol': 'http',
            'user': user,
            'email': user.email,
            'uid': urlsafe_base64_encode(force_bytes(user.pk)),
            'token': default_token_generator.make_token(user)
        }
        targets.append((user.email, context))

    mass_email(targets, subject_template='fair_projects/email/forced_password_reset_subject.txt',
               text_template='fair_projects/email/forced_password_reset.txt',
               html_template='fair_projects/email/forced_password_reset.html')
    messages.add_message(request, messages.INFO, 'Password reset links sent')

send_password_reset.short_description = 'Send password reset links to selected users'
django.contrib.auth.admin.UserAdmin.actions.append(send_password_reset)

# Register your models here.
admin.site.register(School)
