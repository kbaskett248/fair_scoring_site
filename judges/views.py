from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.forms import inlineformset_factory
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse_lazy
from django.views.generic.edit import CreateView
from django.contrib.auth.forms import UserCreationForm as UserForm

from judges.models import Judge

class UserCreationForm(UserForm):
    """The summary line for a class docstring should fit on one line.

    If the class has public attributes, they may be documented here
    in an ``Attributes`` section and follow the same formatting as a
    function's ``Args`` section. Alternatively, attributes may be documented
    inline with the attribute's declaration (see __init__ method below).

    Properties created with the ``@property`` decorator should be documented
    in the property's getter method.

    Attributes:
        attr1 (str): Description of `attr1`.
        attr2 (:obj:`int`, optional): Description of `attr2`.

    """
    Meta = UserForm.Meta
    Meta.fields = ('username',
                   'password1',
                   'password2',
                   'first_name',
                   'last_name',
                   'email')


JudgeFormset = inlineformset_factory(User, Judge,
                                     fields=['user',
                                             'phone',
                                             'has_device',
                                             'education',
                                             'fair_experience',
                                             'categories',
                                             'divisions',
                                             ],
                                     min_num=1, max_num=1, extra=0, can_delete=False,
                                     can_order=False)

class JudgeCreateView(CreateView):
    """The summary line for a class docstring should fit on one line.

    If the class has public attributes, they may be documented here
    in an ``Attributes`` section and follow the same formatting as a
    function's ``Args`` section. Alternatively, attributes may be documented
    inline with the attribute's declaration (see __init__ method below).

    Properties created with the ``@property`` decorator should be documented
    in the property's getter method.

    Attributes:
        attr1 (str): Description of `attr1`.
        attr2 (:obj:`int`, optional): Description of `attr2`.

    """

    model = User
    template_name = 'judges/judge_create.html'
    form_class = UserCreationForm
    success_url = reverse_lazy('login')

    def get_context_data(self, **kwargs):
        context = super(JudgeCreateView, self).get_context_data(**kwargs)
        context['judge_formset'] = self.get_formset(self.request)
        return context

    def get_formset(self, request):
        if request.method == 'POST':
            return JudgeFormset(self.request.POST, self.request.FILES, prefix='judge',
                                queryset=Judge.objects.none(),
                                form_kwargs=self.get_formset_form_kwargs(request))
        else:
            return JudgeFormset(prefix='judge', queryset=Judge.objects.none(),
                                form_kwargs=self.get_formset_form_kwargs(request))

    def get_formset_form_kwargs(self, request):
        return {}

    def post(self, request, *args, **kwargs):
        self.object = None
        fs = self.get_formset(request)
        if fs.is_valid():
            self.formset = fs
            return super(JudgeCreateView, self).post(request, *args, **kwargs)
        else:
            return self.form_invalid(self.get_form(self.get_form_class()))

    @transaction.atomic
    def form_valid(self, form):
        user = form.save()
        self.object = user

        for judge in self.formset.save(commit=False):
            if not judge.user_id:
                judge.user = user
            judge.save()

        return HttpResponseRedirect(self.get_success_url())



