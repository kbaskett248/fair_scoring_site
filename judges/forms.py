from django.contrib.auth.forms import UserCreationForm as UserForm
from django.forms import Form, FileField, ModelForm

from judges.models import Judge


class UploadFileForm(Form):
    file = FileField()


class UserCreationForm(UserForm):
    """Override the built-in user form to gather first_name, last_name and email."""
    Meta = UserForm.Meta
    Meta.fields = ('username',
                   'password1',
                   'password2',
                   'first_name',
                   'last_name',
                   'email')

    def __init__(self, *args, **kwargs):
        """Set the first_name, last_name and email fields to required

        Arguments:
            *args: pass-through form arguments
            **kwargs: pass-through form arguments

        """
        super(UserCreationForm, self).__init__(*args, **kwargs)
        self.fields['first_name'].required = True
        self.fields['last_name'].required = True
        self.fields['email'].required = True


class JudgeCreationForm(ModelForm):
    """Form used for creating a new judge"""

    class Meta:
        model = Judge
        fields = ('phone', 'has_device', 'education', 'fair_experience', 'categories', 'divisions')

