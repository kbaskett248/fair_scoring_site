from django.contrib import admin
from .models import Rubric, Question, Choice


class ChoiceInline(admin.TabularInline):
    model = Choice
    can_delete = True
    verbose_name_plural = 'Choices'
    ordering = ('order', )


class QuestionInline(admin.StackedInline):
    model = Question
    can_delete = True
    ordering = ('order', )


@admin.register(Rubric)
class RubricAdmin(admin.ModelAdmin):
    model = Rubric
    inlines = (QuestionInline, )


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    model = Question
    inlines = (ChoiceInline, )

