from typing import Any, Optional

from django import forms
from django.contrib import admin
from django.db import models
from django.http import HttpRequest

from apps.rubrics.constants import FeedbackFormModuleType
from apps.rubrics.forms import ChoiceForm, QuestionForm
from apps.rubrics.models.feedback_form import ScoreTableFeedbackModule

from .models import (
    Choice,
    ChoiceResponseListFeedbackModule,
    FeedbackForm,
    FeedbackModule,
    MarkdownFeedbackModule,
    Question,
    Rubric,
)


class ChoiceInline(admin.TabularInline):
    model = Choice
    can_delete = True
    verbose_name_plural = "Choices"
    ordering = ("order",)
    form = ChoiceForm


class QuestionInline(admin.TabularInline):
    model = Question
    can_delete = True

    ordering = ("order", "short_description")
    fields = ("order", "short_description", "weight", "question_type")


@admin.register(Rubric)
class RubricAdmin(admin.ModelAdmin):
    model = Rubric
    inlines = (QuestionInline,)


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    model = Question
    form = QuestionForm
    inlines = (ChoiceInline,)
    list_display = (
        "rubric",
        "order",
        "short_description",
        "question_type",
        "num_choices_display",
    )

    ordering = ("rubric", "order", "short_description")


class FeedbackModuleInline(admin.StackedInline):
    MODULE = None

    can_delete = True
    fields = ("order", "module_type")
    instance = None
    model = FeedbackModule
    verbose_name_plural = "Add more feedback modules"

    def get_readonly_fields(
        self, request: HttpRequest, obj: Optional[FeedbackModule] = ...
    ) -> list[str] | tuple[Any, ...]:
        if self.instance:
            return ["module_type"]
        return []

    def get_queryset(self, request: HttpRequest) -> models.QuerySet[Any]:
        qs = super().get_queryset(request)
        if self.instance:
            return qs.filter(pk=self.instance.pk)
        return qs.filter(pk__isnull=True)

    def get_extra(
        self, request: HttpRequest, obj: Optional[FeedbackForm] = ..., **kwargs: Any
    ) -> int:
        if self.instance:
            return 0
        return super().get_extra(request, obj, **kwargs)

    def has_add_permission(self, request: HttpRequest, obj) -> bool:
        if self.instance:
            return False
        return super().has_add_permission(request, obj)


class MarkdownFeedbackModuleInline(FeedbackModuleInline):
    MODULE = FeedbackFormModuleType.MARKDOWN

    fields = ["order", "content"]
    model = MarkdownFeedbackModule
    max_num = 1
    verbose_name = "Change Markdown Module"
    verbose_name_plural = "Markdown Module"


class ScoreTableFeedbackModuleInline(FeedbackModuleInline):
    MODULE = FeedbackFormModuleType.SCORE_TABLE

    fields = [
        "order",
        "questions",
        "include_short_description",
        "include_long_description",
        "table_title",
        "short_description_title",
        "long_description_title",
        "score_title",
        "use_weighted_scores",
        "remove_empty_scores",
    ]
    model = ScoreTableFeedbackModule
    max_num = 1
    verbose_name = "Change Score Table Module"
    verbose_name_plural = "Score Table"


class ChoiceResponseListFeedbackModuleInline(FeedbackModuleInline):
    MODULE = FeedbackFormModuleType.CHOICE_RESPONSE_LIST

    fields = [
        "order",
        "question",
        "display_description",
        "remove_duplicates",
    ]
    model = ChoiceResponseListFeedbackModule
    max_num = 1
    verbose_name = "Change Choice Response List Module"
    verbose_name_plural = "Choice Response List"


@admin.register(FeedbackForm)
class FeedbackFormAdmin(admin.ModelAdmin):
    model = FeedbackForm

    def get_inlines(self, request, obj: FeedbackForm):
        inlines = []
        for module in obj.modules.all():
            module_type = module.module_type

            for base_inline in FeedbackModuleInline.__subclasses__():
                if module_type == base_inline.MODULE:
                    inlines.append(
                        type(
                            f"Single{base_inline.__name__}",
                            (base_inline,),
                            {"instance": module},
                        )
                    )

                    break

        inlines.append(FeedbackModuleInline)

        return inlines

    def save_related(self, request: Any, form: Any, formsets: Any, change: Any) -> None:
        super().save_related(request, form, formsets, change)

        # Iterate over the modules in the form and update order where needed
        feedback_form = form.instance
        for order, module in enumerate(feedback_form.modules.all(), start=1):
            if module.order != order:
                module.order = order
                module.save()
