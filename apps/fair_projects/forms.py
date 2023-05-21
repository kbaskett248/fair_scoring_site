from django.forms import FileField, Form, ModelForm, inlineformset_factory

from apps.fair_projects.models import Project, Student


class UploadFileForm(Form):
    file = FileField()


class StudentForm(ModelForm):
    class Meta:
        model = Student
        fields = (
            "first_name",
            "last_name",
            "gender",
            "ethnicity",
            "grade_level",
            "email",
            "teacher",
        )

    def __init__(self, *args, **kwargs):
        user_is_teacher = kwargs.pop("user_is_teacher", False)
        super().__init__(*args, **kwargs)

        if user_is_teacher:
            del self.fields["teacher"]


StudentFormset = inlineformset_factory(
    Project,
    Student,
    form=StudentForm,
    # fields=('first_name', 'last_name', 'gender', 'ethnicity', 'grade_level', 'email'),
    min_num=1,
    max_num=4,
    extra=3,
    can_delete=False,
)
