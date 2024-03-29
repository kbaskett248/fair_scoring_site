import django.contrib.auth.admin
from django import forms
from django.contrib import admin, messages
from django.contrib.auth.tokens import default_token_generator
from django.contrib.sites.shortcuts import get_current_site
from django.db import transaction
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from import_export import fields, resources
from import_export.admin import ImportExportMixin
from import_export.widgets import CharWidget, ForeignKeyWidget, IntegerWidget

from apps.fair_categories.models import Category, Division, Ethnicity, Subcategory
from apps.fair_projects.logic import mass_email
from apps.fair_projects.models import JudgingInstance
from apps.rubrics.models.rubric import RubricResponse
from fair_scoring_site.logic import get_judging_rubric

from .models import Project, School, Student, Teacher


class ProjectResource(resources.ModelResource):
    category = fields.Field(
        attribute="category",
        column_name="category",
        widget=ForeignKeyWidget(Category, "short_description"),
    )
    subcategory = fields.Field(
        attribute="subcategory",
        column_name="subcategory",
        widget=ForeignKeyWidget(Subcategory, "short_description"),
    )
    division = fields.Field(
        attribute="division",
        column_name="division",
        widget=ForeignKeyWidget(Division, "short_description"),
    )

    class Meta:
        model = Project
        fields = ("number", "title", "category", "subcategory", "division")
        export_order = ("number", "title", "category", "subcategory", "division")
        import_id_fields = ("number",)

    def get_instance(self, instance_loader, row):
        number = self.fields["number"].clean(row)
        title = self.fields["title"].clean(row)
        instance = None

        if number:
            try:
                instance = self.get_queryset().get(number=number)
            except Project.DoesNotExist:
                pass
        elif title:
            try:
                instance = self.get_queryset().get(title=title)
            except Project.DoesNotExist:
                pass

        return instance


class StudentResource(resources.ModelResource):
    class Meta:
        model = Student
        fields = (
            "first_name",
            "last_name",
            "gender",
            "ethnicity",
            "grade_level",
            "email",
            "teacher",
            "project_number",
            "project_title",
        )
        export_order = (
            "first_name",
            "last_name",
            "gender",
            "ethnicity",
            "grade_level",
            "email",
            "teacher",
            "project_number",
            "project_title",
        )
        import_id_fields = ("first_name", "last_name")

    class TeacherForeignKeyWidget(ForeignKeyWidget):
        """Allow value formats of <last name> or <first name> <last name>."""

        def clean(self, value, row=None, *args, **kwargs):
            result = None
            try:
                result = super().clean(value.split()[1], row, *args, **kwargs)
            except IndexError:
                pass
            finally:
                if result:
                    return result
                else:
                    return super().clean(value, row, *args, **kwargs)

    first_name = fields.Field(
        attribute="first_name", column_name="first name", widget=CharWidget()
    )
    last_name = fields.Field(
        attribute="last_name", column_name="last name", widget=CharWidget()
    )
    grade_level = fields.Field(
        attribute="grade_level", column_name="grade level", widget=IntegerWidget()
    )
    ethnicity = fields.Field(
        attribute="ethnicity",
        column_name="ethnicity",
        widget=ForeignKeyWidget(Ethnicity, "short_description"),
    )
    teacher = fields.Field(
        attribute="teacher",
        column_name="teacher",
        widget=TeacherForeignKeyWidget(Teacher, "user__last_name"),
    )
    project_number = fields.Field(
        attribute="project",
        column_name="project number",
        widget=ForeignKeyWidget(Project, "number"),
    )
    project_title = fields.Field(
        attribute="project",
        column_name="project title",
        widget=ForeignKeyWidget(Project, "title"),
        readonly=True,
    )


class StudentInline(admin.StackedInline):
    model = Student
    min_num = 1
    extra = 1


class JudgingInstanceForm(forms.ModelForm):
    class Meta:
        model = JudgingInstance
        fields = ("judge",)

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
    fields = ("judge", "rubric", "score")
    readonly_fields = ("rubric", "score")

    def rubric(self, instance):
        return instance.response.rubric


@admin.register(Project)
class ProjectAdmin(ImportExportMixin, admin.ModelAdmin):
    model = Project
    list_display = ("number", "title", "category", "subcategory", "division")
    list_display_links = ("number", "title")
    list_filter = ("category", "division")
    ordering = ("number", "title")
    inlines = (StudentInline, JudgingInstanceInline)
    view_on_site = True
    save_on_top = True

    resource_class = ProjectResource


@admin.register(Student)
class StudentAdmin(ImportExportMixin, admin.ModelAdmin):
    model = Student
    list_display = ("full_name", "teacher", "grade_level", "project_title")
    list_filter = ("teacher", "grade_level", "project__category", "project__division")
    ordering = ("last_name", "first_name")

    resource_class = StudentResource

    def full_name(self, obj):
        return obj.full_name

    full_name.admin_order_field = "last_name"

    def project_title(self, obj):
        try:
            return obj.project.title
        except AttributeError:
            return "-"

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("project", "teacher", "teacher__user")
        )


@admin.register(JudgingInstance)
class InstanceAdmin(admin.ModelAdmin):
    model = JudgingInstance
    list_display = (
        "project_number",
        "project_title",
        "judge_name",
        "rubric_name",
        "locked",
        "has_response",
        "complete",
        "response_score",
    )
    ordering = ("project__number", "project__title", "judge__user__last_name")
    readonly_fields = ("judge", "response", "project", "locked")
    search_fields = ("project__title", "project__number")

    def project_number(self, obj):
        return obj.project.number

    project_number.admin_order_field = "project__number"

    def project_title(self, obj):
        return obj.project.title

    project_title.admin_order_field = "project__title"

    def judge_name(self, obj):
        return str(obj.judge.user.get_full_name())

    judge_name.admin_order_field = "judge__user__last_name"

    def judge_last_name(self, obj):
        return obj.judge.user.last_name

    def rubric_name(self, obj):
        return obj.response.rubric.name

    def response_score(self, obj):
        return obj.response.score()

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related(
                "project", "judge", "judge__user", "response", "response__rubric"
            )
            .prefetch_related("response__questionresponse_set")
        )

    def has_add_permission(self, request, obj=None):
        return False


class TeacherInline(admin.StackedInline):
    model = Teacher
    can_delete = False
    max_num = 1
    verbose_name_plural = "Teacher Information"

    @classmethod
    def condition(cls, request, obj=None):
        return obj and obj.has_perm("fair_projects.is_teacher")


django.contrib.auth.admin.UserAdmin.register_conditional_inline(TeacherInline)


def send_password_reset(modeladmin, request, queryset):
    current_site = get_current_site(request)
    site_name = current_site.name
    domain = current_site.domain

    targets = []
    for user in queryset:
        context = {
            "domain": domain,
            "site_name": site_name,
            "protocol": "http",
            "user": user,
            "email": user.email,
            "uid": urlsafe_base64_encode(force_bytes(user.pk)),
            "token": default_token_generator.make_token(user),
        }
        targets.append((user.email, context))

    mass_email(
        targets,
        subject_template="fair_projects/email/forced_password_reset_subject.txt",
        text_template="fair_projects/email/forced_password_reset.txt",
        html_template="fair_projects/email/forced_password_reset.html",
    )
    messages.add_message(request, messages.INFO, "Password reset links sent")


send_password_reset.short_description = "Send password reset links to selected users"
django.contrib.auth.admin.UserAdmin.actions = [
    *django.contrib.auth.admin.UserAdmin.actions,
    send_password_reset,
]

# Register your models here.
admin.site.register(School)

from .views import delete_judge_assignments, judge_assignment


def do_judge_assignment(modeladmin, request, queryset):
    return judge_assignment(request)


do_judge_assignment.short_description = "Assign Judges"
ProjectAdmin.actions = [
    *ProjectAdmin.actions,
    do_judge_assignment,
]


def do_judge_deletion(modeladmin, request, queryset):
    return delete_judge_assignments(request)


do_judge_deletion.short_description = "Delete Judge assignments"
ProjectAdmin.actions.append(do_judge_deletion)
