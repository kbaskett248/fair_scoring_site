from django.contrib import admin

from apps.rubrics.forms import ChoiceForm, QuestionForm

from .models.rubric import Choice, Question, Rubric


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
