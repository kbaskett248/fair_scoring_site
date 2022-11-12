from django.contrib import admin, messages
from django.contrib.contenttypes.admin import GenericTabularInline
from django.contrib.contenttypes.forms import BaseGenericInlineFormSet
from django.core.exceptions import ValidationError
from django.db.models.base import Model
from django.urls.base import reverse
from django.utils.html import format_html
from django.utils.translation import gettext as _
from import_export import fields, resources
from import_export.admin import ExportMixin

import apps.awards.admin
import apps.fair_projects
from apps.awards.logic import InstanceBase, assign_awards
from apps.awards.models import Award, AwardInstance
from apps.fair_categories.models import Category, Division, Ethnicity, Subcategory
from apps.fair_projects.logic import get_projects_sorted_by_score
from apps.fair_projects.models import Project, Student

# This seems like a safe place to register signals
from . import signals

admin.site.unregister(Project)
admin.site.unregister(Award)
admin.site.unregister(AwardInstance)


def assign_awards_to_projects(modeladmin, request, queryset):
    instances = [ProjectInstance(project) for project in get_projects_sorted_by_score()]
    assign_awards(queryset, instances)
    for instance in instances:
        if instance.awards:
            messages.add_message(
                request,
                messages.INFO,
                "Assigned {0} to {1}".format(instance.awards_str, instance.project),
            )
    messages.add_message(request, messages.INFO, "Awards assigned")


assign_awards_to_projects.short_description = "Assign selected awards to projects"


class ProjectInstance(InstanceBase):
    model_attr = "project"

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
        return max(
            (student.grade_level for student in self.project.student_set.all()),
            default=None,
        )


class AwardInstanceResource(resources.ModelResource):
    award = fields.Field()
    project = fields.Field()
    students = fields.Field()
    category = fields.Field()
    division = fields.Field()

    class Meta:
        model = AwardInstance
        fields = ("award", "project", "students", "category", "division")
        export_order = ("award", "project", "students", "category", "division")

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


class AwardRuleForm(apps.awards.admin.AwardRuleForm):
    traits = ("category", "subcategory", "division", "number", "grade_level")

    def generic_validation(self, model: Model, key: str, fields: dict):
        for value in self.individual_value_iterator(**fields):
            filters = {key: value}
            if not model.objects.filter(**filters).exists():
                params = fields.copy()
                params["value"] = value
                self.raise_default_validation_error(params)

    def validate_category(self, **fields):
        self.generic_validation(Category, "short_description", fields)

    def validate_subcategory(self, **fields):
        self.generic_validation(Subcategory, "short_description", fields)

    def validate_division(self, **fields):
        self.generic_validation(Division, "short_description", fields)

    def validate_number(self, **fields):
        self.generic_validation(Project, "number", fields)

    def validate_grade_level(self, **fields):
        for value in self.individual_value_iterator(**fields):
            if not value.isdecimal() or not 1 <= int(value) <= 12:
                params = fields.copy()
                params["value"] = value
                raise ValidationError(
                    "Values for the %(trait)s trait must be numbers between 1 and 12",
                    code="invalid trait value",
                    params=params,
                )


class AwardRuleInline(apps.awards.admin.AwardRuleInline):
    form = AwardRuleForm


class AwardInstanceInline(apps.awards.admin.AwardInstanceInline):
    readonly_fields = (
        "project_number",
        "project_title",
        "project_students",
        "project_category",
        "project_division",
    )

    def admin_link(self, instance, text):
        return format_html(
            '<a href="{0}">{1}</a>',
            reverse(
                "admin:fair_projects_project_change", args=(instance.content_object.pk,)
            ),
            text,
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
        return reverse("fair_projects:detail", args=(instance.content_object.number,))


class TraitListFilter(apps.awards.admin.TraitListFilter):
    award_rule_form_class = AwardRuleForm


@admin.register(Award)
class AwardAdmin(apps.awards.admin.AwardAdmin):
    actions = (assign_awards_to_projects,)
    inlines = (AwardRuleInline, AwardInstanceInline)
    list_filter = (TraitListFilter,)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


@admin.register(AwardInstance)
class AwardInstanceAdmin(ExportMixin, apps.awards.admin.AwardInstanceAdmin):
    list_filter = ("award", TraitListFilter)
    list_display = ("award", "project", "students", "category", "division")
    fields = ("award", "project", "students", "category", "division")
    readonly_fields = ("award", "project", "students", "category", "division")

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
            elif form.cleaned_data["DELETE"]:
                continue
            self.clean_award(project_instance, form.cleaned_data["award"])

    def clean_award(self, instance, award):
        if not award.instance_passes_all_rules(instance):
            raise ValidationError(
                _("%(award)s is not valid for this project"),
                code="invalid award for project",
                params={"award": award},
            )
        elif award.exclude_from_instance(instance):
            raise ValidationError(
                _("Cannot assign %(award)s to this project due to excluded awards"),
                code="excluded award for project",
                params={"award": award},
            )


class ProjectAwardInline(GenericTabularInline):
    model = AwardInstance
    formset = ProjectAwardFormset


@admin.register(Project)
class ProjectAdmin(apps.fair_projects.admin.ProjectAdmin):
    inlines = list(apps.fair_projects.admin.ProjectAdmin.inlines) + [ProjectAwardInline]
