from django import forms

from .models import Question

class RubricForm(forms.Form):
    def __init__(self, rubric, *args, **kwargs):
        super(RubricForm, self).__init__(*args, **kwargs)

        for i, question in enumerate(rubric.question_set.all()):
            self.fields['question_%s' % i] = self.build_form_field(question)

    def build_form_field(self, question):
        field = None
        if question.question_type == Question.LONG_TEXT:
            field = forms.CharField(label=question.description(), help_text=question.help_text,
                                    strip=True, widget=forms.Textarea)
        elif question.question_type == Question.SCALE_TYPE:
            field = forms.ChoiceField(label=question.description(), help_text=question.help_text,
                                      choices=question.choices, widget=forms.RadioSelect)
        elif question.question_type == Question.SINGLE_SELECT_TYPE:
            field = forms.ChoiceField(label=question.description(), help_text=question.help_text,
                                      choices=question.choices, widget=forms.RadioSelect)
        elif question.question_type == Question.MULTI_SELECT_TYPE:
            field = forms.ChoiceField(label=question.description(), help_text=question.help_text,
                                      choices=question.choices, widget=forms.CheckboxSelectMultiple)

        return field
