from django.contrib.auth.models import User, Group
from django.db import transaction
from django.http import HttpResponseRedirect
from django.urls import reverse_lazy
from django.views.generic.edit import CreateView

from .forms import UserCreationForm, JudgeCreationForm


class JudgeCreateView(CreateView):
    """Use to create a new Judge.

    This view is used to create a new Judge and the corresponding User object.
    In addition to gathering all the necessary fields, it ensures the Judge's
    User object has been added to the Judges group.

    """

    model = User
    template_name = "judges/judge_create.html"
    form_class = UserCreationForm
    success_url = reverse_lazy("login")

    def get_context_data(self, **kwargs):
        """Add the formset for Judge fields to the context."""
        context = super(JudgeCreateView, self).get_context_data(**kwargs)
        context["judge_form"] = self.get_judge_form(self.request)
        return context

    def get_judge_form(self, request) -> JudgeCreationForm:
        if request.method == "POST":
            return JudgeCreationForm(
                self.request.POST, self.request.FILES, prefix="judge"
            )
        else:
            return JudgeCreationForm(prefix="judge")

    def post(self, request, *args, **kwargs):
        self.object = None

        judge_form = self.get_judge_form(request)
        if judge_form.is_valid():
            self.judge_form = judge_form
            return super(JudgeCreateView, self).post(request, *args, **kwargs)
        else:
            return self.form_invalid(self.get_form(self.get_form_class()))

    @transaction.atomic
    def form_valid(self, form):
        user = form.save()
        self.add_user_to_judges_group(user)
        user.save()
        self.object = user

        judge = self.judge_form.save(commit=False)
        if not judge.user_id:
            judge.user = user
        judge.save()
        self.judge_form.save_m2m()

        return HttpResponseRedirect(self.get_success_url())

    def add_user_to_judges_group(self, user):
        judges_group = Group.objects.get(name="Judges")
        user.groups.add(judges_group.pk)
