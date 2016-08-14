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
    inlines = (ChoiceInline, )

    def get_formsets(self, request, obj=None):
        for inline in self.get_inline_instances(request, obj):
            if isinstance(inline, ChoiceInline):
                if obj and obj.show_choices():
                    yield inline.get_formset(request, obj)
                else:
                    continue
            else:
                yield inline.get_formset(request, obj)


@admin.register(Rubric)
class RubricAdmin(admin.ModelAdmin):
    model = Rubric
    inlines = (QuestionInline, )

