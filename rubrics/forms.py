from collections import defaultdict

from django import forms

from .models import Question, RubricResponse, Rubric

def default_field(question):
    return forms.CharField(label=question.description(), help_text=question.help_text,
                           strip=True, required=question.required)


def long_text_field(question):
    return forms.CharField(label=question.description(), help_text=question.help_text,
                           strip=True, required=question.required, widget=forms.Textarea)


def scale_field(question):
    return forms.ChoiceField(label=question.description(), help_text=question.help_text,
                             choices=question.choices, required=question.required, widget=forms.RadioSelect)


def single_select_field(question):
    return forms.ChoiceField(label=question.description(), help_text=question.help_text,
                             choices=question.choices, required=question.required, widget=forms.RadioSelect)


def multi_select_field(question):
    return forms.MultipleChoiceField(label=question.description(), help_text=question.help_text,
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

    def __init__(self, response_or_rubric=None, template_dict=DEFAULT_TEMPLATE_DICT,
                 field_dict=DEFAULT_FIELD_DICT, **kwargs):
        super(RubricForm, self).__init__(**kwargs)

        if isinstance(response_or_rubric, RubricResponse):
            self.response = response_or_rubric
            self.rubric = self.response.rubric
        elif isinstance(response_or_rubric, Rubric):
            self.rubric = response_or_rubric
            self.response = None
        else:
            raise TypeError('response_or_rubric must be a Rubric or a RubricResponse object')

        self.title = self.rubric.name

        def create_field(question, name):
            field = field_dict.get(question.question_type, default_field)(self, question)
            field.question_type = question.question_type
            field.template = template_dict.get(question.question_type, 'rubrics/default_type.html')

            self.fields[name] = field

        if self.response:
            for q_resp in self.response.questionresponse_set.all():
                create_field(q_resp.question, q_resp.name)
        else:
            for question in self.rubric.question_set.all():
                name = 'question_%s' % question.pk
                create_field(question, name)

    def save_responses(self):
        pass


class NewRubricForm(forms.Form):
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

    def __init__(self, instance=None, **kwargs):
        super(NewRubricForm, self).__init__(**kwargs)
        self.instance = instance

    def save(self, commit=True):
        updated_data = {int(key.replace('question_','')): self.cleaned_data[key]
                        for key in self.changed_data}
        self.instance.update_data(updated_data)
        return self.instance


def rubric_form_factory(rubric, field_dict=NewRubricForm.DEFAULT_FIELD_DICT,
                        template_dict=NewRubricForm.DEFAULT_TEMPLATE_DICT):
    form_name = 'RubricForm%s' % rubric.pk
    form_bases = (NewRubricForm, )
    form_dict = {'title': rubric.name,
                 'rubric': rubric}
    for question in rubric.question_set.all():
        name = 'question_%s' % question.pk
        field = field_dict.get(question.question_type, default_field)(question)
        field.question_type = question.question_type
        field.template = template_dict.get(question.question_type,
                                           'rubrics/default_type.html')
        form_dict[name] = field

    return type(form_name, form_bases, form_dict)
