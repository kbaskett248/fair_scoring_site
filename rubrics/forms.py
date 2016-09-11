from collections import defaultdict

from django import forms

from .models import Question

def default_field(form, question):
    return forms.CharField(label=question.description(), help_text=question.help_text,
                           strip=True)


def long_text_field(form, question):
    return forms.CharField(label=question.description(), help_text=question.help_text,
                           strip=True, widget=forms.Textarea)


def scale_field(form, question):
    return forms.ChoiceField(label=question.description(), help_text=question.help_text,
                             choices=question.choices, widget=forms.RadioSelect)


def single_select_field(form, question):
    return forms.ChoiceField(label=question.description(), help_text=question.help_text,
                             choices=question.choices, widget=forms.RadioSelect)


def multi_select_field(form, question):
    return forms.ChoiceField(label=question.description(), help_text=question.help_text,
                             choices=question.choices, widget=forms.CheckboxSelectMultiple)


class RubricForm(forms.Form):
    DEFAULT_TEMPLATE_DICT = {
        Question.LONG_TEXT: 'rubrics/long_text_type.html',
        Question.SCALE_TYPE: 'rubrics/scale_type.html',
        Question.SINGLE_SELECT_TYPE: 'rubrics/single_select_type.html',
        Question.MULTI_SELECT_TYPE: 'rubrics/multi_select_type.html'
    }

    DEFAULT_FIELD_DICT = {
        Question.LONG_TEXT: long_text_field,
        Question.SCALE_TYPE: scale_field,
        Question.SINGLE_SELECT_TYPE: single_select_field,
        Question.MULTI_SELECT_TYPE: multi_select_field
    }

    def __init__(self, rubric, template_dict=DEFAULT_TEMPLATE_DICT, field_dict=DEFAULT_FIELD_DICT,
                 *args, **kwargs):
        super(RubricForm, self).__init__(*args, **kwargs)

        self.rubric = rubric
        self.title = self.rubric.name

        for i, question in enumerate(rubric.question_set.all()):
            self.fields['question_%s' % i] = field_dict.get(question.question_type, default_field)(
                self, question)
            self.fields['question_%s' % i].question_type = question.question_type
            self.fields['question_%s' % i].template = template_dict.get(question.question_type,
                                                                        'rubrics/default_type.html')


