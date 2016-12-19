from django import forms

from .models import Question


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
        Question.LONG_TEXT: 'rubrics/long_text_type_edit.html',
        Question.SCALE_TYPE: 'rubrics/scale_type_edit.html',
        Question.SINGLE_SELECT_TYPE: 'rubrics/single_select_type_edit.html',
        Question.MULTI_SELECT_TYPE: 'rubrics/multi_select_type_edit.html'
    }

    DEFAULT_FIELD_DICT = {
        Question.LONG_TEXT: long_text_field,
        Question.SCALE_TYPE: scale_field,
        Question.SINGLE_SELECT_TYPE: single_select_field,
        Question.MULTI_SELECT_TYPE: multi_select_field
    }

    def __init__(self, instance=None, **kwargs):
        super(RubricForm, self).__init__(**kwargs)
        self.instance = instance
        d = self.__dict__

    def save(self, commit=True):
        updated_data = {int(key.replace('question_','')): self.cleaned_data[key]
                        for key in self.changed_data}
        self.instance.update_responses(updated_data)
        return self.instance


def rubric_form_factory(rubric, field_dict=RubricForm.DEFAULT_FIELD_DICT,
                        template_dict=RubricForm.DEFAULT_TEMPLATE_DICT):
    form_name = 'RubricForm%s' % rubric.pk
    form_bases = (RubricForm,)
    form_dict = {'title': rubric.name,
                 'rubric': rubric}
    for question in rubric.ordered_question_set.all():
        name = 'question_%s' % question.pk
        field = field_dict.get(question.question_type, default_field)(question)
        field.question_type = question.question_type
        field.template = template_dict.get(question.question_type,
                                           'rubrics/default_type_edit.html')
        form_dict[name] = field

    return type(form_name, form_bases, form_dict)
