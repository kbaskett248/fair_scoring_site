from django.contrib.auth.models import User, Group
from django.db import transaction
from django.http import HttpResponseRedirect
from django.urls import reverse_lazy
from django.views.generic.edit import CreateView

from .forms import UserCreationForm, JudgeFormset
from .models import Judge

class JudgeCreateView(CreateView):
    """Use to create a new Judge.

    This view is used to create a new Judge and the corresponding User object.
    In addition to gathering all the necessary fields, it ensures the Judge's
    User object has been added to the Judges group.

    """

    model = User
    template_name = 'judges/judge_create.html'
    form_class = UserCreationForm
    success_url = reverse_lazy('login')

    def get_context_data(self, **kwargs):
        """Add the formset for Judge fields to the context."""
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
        self.add_user_to_judges_group(user)
        user.save()
        self.object = user

        for judge in self.formset.save(commit=False):
            if not judge.user_id:
                judge.user = user
            judge.save()
        self.formset.save_m2m()

        return HttpResponseRedirect(self.get_success_url())

    def add_user_to_judges_group(self, user):
        judges_group = Group.objects.get(name='Judges')
        user.groups.add(judges_group.pk)



