from collections import defaultdict

from django import forms

from .models import Question, RubricResponse, Rubric

def default_field(form, question):
    return forms.CharField(label=question.description(), help_text=question.help_text,
                           strip=True, required=question.required)


def long_text_field(form, question):
    return forms.CharField(label=question.description(), help_text=question.help_text,
                           strip=True, required=question.required, widget=forms.Textarea)


def scale_field(form, question):
    return forms.ChoiceField(label=question.description(), help_text=question.help_text,
                             choices=question.choices, required=question.required, widget=forms.RadioSelect)


def single_select_field(form, question):
    return forms.ChoiceField(label=question.description(), help_text=question.help_text,
                             choices=question.choices, required=question.required, widget=forms.RadioSelect)


def multi_select_field(form, question):
    return forms.ChoiceField(label=question.description(), help_text=question.help_text,
                             choices=question.choices, required=question.required, widget=forms.CheckboxSelectMultiple)


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

    def __init__(self, response_or_rubric, template_dict=DEFAULT_TEMPLATE_DICT,
                 field_dict=DEFAULT_FIELD_DICT, **kwargs):
        super(RubricForm, self).__init__(**kwargs)

        if isinstance(response_or_rubric, RubricResponse):
            self.response = response_or_rubric
            self.rubric = self.response.rubric
            self.is_bound = True
        else:
            self.rubric = response_or_rubric
            self.response = None

        self.title = self.rubric.name

        def create_field(question, name):
            field = field_dict.get(question.question_type, default_field)(self, question)
            field.question_type = question.question_type
            field.template = template_dict.get(question.question_type, 'rubrics/default_type.html')

            self.fields[name] = field

        if self.response:
            for q_resp in self.response.questionresponse_set.all():
                name = 'question_%s' % q_resp.pk
                create_field(q_resp.question, name)
                try:
                    self.data[name]
                except KeyError:
                    self.data[name] = q_resp.response
        else:
            for question in self.rubric.question_set.all():
                name = 'question_%s' % question.pk
                create_field(question, name)

    def save_responses(self):
        pass
