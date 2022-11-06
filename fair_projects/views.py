import functools
import logging
from collections import defaultdict, namedtuple

from django.contrib import messages
from django.contrib.auth.mixins import (
    AccessMixin,
    PermissionRequiredMixin,
    UserPassesTestMixin,
)
from django.contrib.auth.models import User
from django.contrib.sites.shortcuts import get_current_site
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.http import Http404
from django.http import HttpResponseRedirect
from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.csrf import csrf_protect
from django.views.generic import DetailView, ListView
from django.views.generic import TemplateView
from django.views.generic.edit import UpdateView, CreateView, DeleteView
from django.urls import reverse, reverse_lazy

from awards.models import Award
from fair_projects.logic import get_rubric_name
from judges.models import Judge
from rubrics.forms import rubric_form_factory
from rubrics.models import Question
from .forms import UploadFileForm, StudentFormset
from .logic import (
    handle_project_import,
    email_teachers,
    get_projects_sorted_by_score,
    assign_judges,
    get_question_feedback_dict,
)
from .models import Project, Student, JudgingInstance, Teacher

logger = logging.getLogger(__name__)


class ProjectIndex(ListView):
    template_name = "fair_projects/index.html"
    model = Project
    queryset = Project.objects.select_related(
        "category", "subcategory", "division"
    ).order_by("number", "title")
    context_object_name = "project_list"

    def get_context_data(self, **kwargs):
        context = super(ProjectIndex, self).get_context_data(**kwargs)

        request_user = self.request.user
        context["allow_create"] = False
        if request_user.is_authenticated:
            if request_user.has_perm("fair_projects.add_project"):
                context["allow_create"] = True

        return context


class ProjectModifyMixin(PermissionRequiredMixin):
    model = Project
    fields = (
        "title",
        "category",
        "subcategory",
        "division",
        "abstract",
        "requires_attention",
        "judge_notes",
    )
    slug_url_kwarg = "project_number"
    slug_field = "number"

    def get_success_url(self):
        return reverse("fair_projects:detail", args=(self.object.number,))

    def get_context_data(self, **kwargs):
        context = super(ProjectModifyMixin, self).get_context_data(**kwargs)
        context["student_formset"] = self.get_student_formset(self.request)
        return context

    def get_student_formset(self, request):
        raise NotImplementedError("Implement get_student_formset().")

    def get_formset_form_kwargs(self, request):
        try:
            Teacher.objects.get(user=request.user)
        except ObjectDoesNotExist:
            user_is_teacher = False
        else:
            user_is_teacher = True
        finally:
            return {"user_is_teacher": user_is_teacher}

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        fs = self.get_student_formset(request)
        if fs.is_valid():
            self.student_formset = fs
            return super(ProjectModifyMixin, self).post(request, *args, **kwargs)
        else:
            return self.form_invalid(self.get_form(self.get_form_class()))

    @transaction.atomic
    def form_valid(self, form):
        project = form.save()
        self.object = project

        for student in self.student_formset.save(commit=False):
            if not student.project_id:
                student.project = project

            if not student.teacher_id:
                teacher = Teacher.objects.get(user=self.request.user)
                student.teacher = teacher

            student.save()

        return HttpResponseRedirect(self.get_success_url())


class ProjectCreate(ProjectModifyMixin, CreateView):
    template_name = "fair_projects/project_create.html"
    permission_required = "fair_projects.add_project"

    def get_student_formset(self, request):
        if request.method == "POST":
            return StudentFormset(
                self.request.POST,
                self.request.FILES,
                prefix="Students",
                queryset=Project.objects.none(),
                form_kwargs=self.get_formset_form_kwargs(request),
            )
        else:
            return StudentFormset(
                prefix="Students",
                queryset=Project.objects.none(),
                form_kwargs=self.get_formset_form_kwargs(request),
            )

    def get_object(self, queryset=None):
        return None


class ProjectUpdate(ProjectModifyMixin, UpdateView):
    template_name = "fair_projects/project_update.html"
    permission_required = "fair_projects.change_project"

    def get_student_formset(self, request):
        if request.method == "POST":
            return StudentFormset(
                self.request.POST,
                self.request.FILES,
                prefix="Students",
                instance=self.object,
                form_kwargs=self.get_formset_form_kwargs(request),
            )
        else:
            return StudentFormset(
                prefix="Students",
                instance=self.object,
                form_kwargs=self.get_formset_form_kwargs(request),
            )


class ProjectDelete(PermissionRequiredMixin, DeleteView):
    template_name = "fair_projects/project_delete.html"
    permission_required = "fair_projects.delete_project"
    model = Project
    slug_url_kwarg = "project_number"
    slug_field = "number"
    success_url = reverse_lazy("fair_projects:index")


class ProjectDetail(DetailView):
    template_name = "fair_projects/detail.html"
    model = Project
    context_object_name = "project"
    queryset = Project.objects.select_related("category", "subcategory", "division")

    def get_object(self, queryset=None):
        if not queryset:
            queryset = self.queryset

        try:
            return queryset.get(number=self.kwargs["project_number"])
        except ObjectDoesNotExist:
            raise Http404()

    def get_context_data(self, **kwargs):
        context = super(ProjectDetail, self).get_context_data(**kwargs)

        context["student_list"] = Student.objects.filter(project=self.object)
        judge_instances = JudgingInstance.objects.filter(project=self.object)
        context["judge_list"] = [ji.judge for ji in judge_instances]

        request_user = self.request.user
        context["is_submitting_teacher"] = False
        if request_user.is_authenticated:
            if request_user.is_superuser:
                context["is_submitting_teacher"] = True
            elif request_user.has_perm("fair_projects.is_teacher"):
                teacher = Teacher.objects.get(user=request_user)
                if [
                    student
                    for student in context["student_list"]
                    if student.teacher == teacher
                ]:
                    context["is_submitting_teacher"] = True

        return context


class ResultsIndex(PermissionRequiredMixin, AccessMixin, TemplateView):
    template_name = "fair_projects/results.html"
    permission_required = "fair_projects.can_view_results"
    permission_denied_message = "This user has no access to the Results page."

    def get_context_data(self, **kwargs):
        context = super(ResultsIndex, self).get_context_data(**kwargs)

        context["project_list"] = get_projects_sorted_by_score()
        for project in context["project_list"]:
            project.awards = Award.get_awards_for_object(project)

        return context


def delete_judge_assignments(request):
    _, deletion_dict = JudgingInstance.objects.all().delete()
    msg = "\n".join(
        [
            "Deleted {0} {1} objects".format(count, obj)
            for obj, count in deletion_dict.items()
        ]
    )
    messages.add_message(request, messages.INFO, msg)
    return HttpResponseRedirect("/admin/fair_projects/project/")


def judge_assignment(request):
    assign_judges()
    messages.add_message(request, messages.INFO, "Judge assignment complete")
    return HttpResponseRedirect("/admin/fair_projects/project/")


@csrf_protect
def import_projects(request):
    logger.info("Import Projects; request=%s", request)
    c = {}
    if request.method == "POST":
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            handle_project_import(request.FILES["file"])
            return HttpResponseRedirect("/admin/fair_projects/project/")
    else:
        form = UploadFileForm()

    request.current_app = "fair_projects"
    c.update({"form": form})
    return render(request, "fair_projects/project_upload.html", c)


def notify_teachers(request):
    current_site = get_current_site(request)
    site_name = current_site.name
    domain = current_site.domain

    email_teachers(site_name, domain)

    messages.add_message(request, messages.INFO, "Notifications sent")
    return HttpResponseRedirect(reverse("admin:auth_user_changelist"))


class SpecificUserRequiredMixin(AccessMixin):
    allow_superuser = False
    allow_staff = False

    def get_required_user(self, *args, **kwargs):
        raise NotImplementedError(
            "{0} is missing the implementation of the get_user_from_path() method.".format(
                self.__class__.__name__
            )
        )

    def dispatch(self, request, *args, **kwargs):
        current_user = self.request.user
        required_user = self.get_required_user(*args, **kwargs)

        if not current_user.is_authenticated:
            return self.handle_no_permission()

        if self.allow_superuser and current_user.is_superuser:
            return super(SpecificUserRequiredMixin, self).dispatch(
                request, *args, **kwargs
            )

        if self.allow_staff and current_user.is_staff:
            return super(SpecificUserRequiredMixin, self).dispatch(
                request, *args, **kwargs
            )

        if current_user != required_user:
            return self.handle_no_permission()

        return super(SpecificUserRequiredMixin, self).dispatch(request, *args, **kwargs)


class JudgeIndex(UserPassesTestMixin, ListView):
    template_name = "fair_projects/judge_index.html"
    model = Judge
    queryset = Judge.objects.select_related("user").order_by(
        "user__last_name", "user__first_name"
    )
    context_object_name = "judge_list"

    def user_is_staff(self):
        return self.request.user.is_active and self.request.user.is_staff

    test_func = user_is_staff


class JudgeDetail(SpecificUserRequiredMixin, ListView):
    allow_superuser = True
    allow_staff = True
    template_name = "fair_projects/judge_detail.html"
    context_object_name = "judginginstance_list"

    def get_required_user(self, *args, **kwargs):
        return get_object_or_404(User, username=kwargs["judge_username"])

    def get_queryset(self):
        self.judge = get_object_or_404(
            Judge, user__username=self.kwargs["judge_username"]
        )
        return (
            JudgingInstance.objects.filter(
                judge=self.judge, response__rubric__name=get_rubric_name()
            )
            .order_by("project__number")
            .select_related("project", "project__category", "project__division")
        )

    def get_context_data(self, **kwargs):
        context = super(JudgeDetail, self).get_context_data(**kwargs)
        context["judge"] = self.judge
        context["show_needs_attention"] = True
        return context


class JudgingInstanceMixin(SpecificUserRequiredMixin):
    allow_superuser = True
    allow_staff = True
    template_name = "fair_projects/judging_instance_detail.html"
    pk_url_kwarg = "judginginstance_key"
    model = JudgingInstance
    queryset = JudgingInstance.objects.select_related(
        "judge", "project", "response", "judge__user"
    )
    context_object_name = "judging_instance"

    def get_required_user(self, *args, **kwargs):
        self.judging_instance = self.queryset.get(pk=kwargs[self.pk_url_kwarg])

        self.judge = self.judging_instance.judge
        user_name = self.judge.user.username
        return get_object_or_404(User, username=user_name)

    def get_context_data(self, **kwargs):
        context = super(JudgingInstanceMixin, self).get_context_data(**kwargs)

        context["judge"] = self.judge
        project = self.judging_instance.project
        context["project"] = project
        context["student_list"] = project.student_set.all()
        context["rubric_response"] = self.judging_instance.response
        context["edit_mode"] = False

        return context

    def dispatch(self, request, *args, **kwargs):
        """If a JudgingInstance can't be found, redirect to the judge's user page.

        Arguments:
            request: a request object
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.

        Returns:
            An HttpResponse or HttpResponseRedirect

        """
        try:
            return super(JudgingInstanceMixin, self).dispatch(request, *args, **kwargs)
        except JudgingInstance.DoesNotExist:
            messages.add_message(
                request,
                messages.INFO,
                "You are no longer assigned to judge that project",
            )
            if Judge.objects.filter(user__username=request.user.username).exists():
                return redirect(
                    "fair_projects:judge_detail", judge_username=request.user.username
                )
            else:
                return redirect("fair_projects:index")


class JudgingInstanceDetail(JudgingInstanceMixin, DetailView):
    template_dict = {
        Question.MULTI_SELECT_TYPE: "rubrics/multi_select_type_view.html",
        Question.LONG_TEXT: "rubrics/long_text_type_view.html",
    }
    default_template = "rubrics/default_type_view.html"

    def get_context_data(self, **kwargs):
        context = super(JudgingInstanceDetail, self).get_context_data(**kwargs)
        template_dict = defaultdict(
            functools.partial(self.get_default_template, **kwargs)
        )
        template_dict.update(self.get_template_dict(**kwargs))
        question_list = [
            (template_dict[question_type], question, answer)
            for question_type, question, answer in context[
                "rubric_response"
            ].question_answer_iter()
        ]
        context["question_list"] = question_list

        return context

    def get_template_dict(self, **kwargs):
        return self.template_dict

    def get_default_template(self, **kwargs):
        return self.default_template


class JudgingInstanceUpdate(JudgingInstanceMixin, UpdateView):
    def get_context_data(self, **kwargs):
        context = super(JudgingInstanceUpdate, self).get_context_data(**kwargs)

        context["edit_mode"] = True
        context["post_url"] = reverse(
            "fair_projects:judging_instance_edit", args=(self.judging_instance.pk,)
        )
        context["rubric_form"] = context["form"]

        return context

    def get_form_class(self):
        required = False
        try:
            if self.submit:
                required = None
        except AttributeError:
            pass
        return rubric_form_factory(
            self.object.response.rubric, override_required=required
        )

    def get_form_kwargs(self):
        kwargs = super(JudgingInstanceUpdate, self).get_form_kwargs()
        kwargs["instance"] = kwargs["instance"].response
        if "data" not in kwargs:
            kwargs["data"] = kwargs["instance"].get_form_data()
        return kwargs

    def get_success_url(self):
        return reverse(
            "fair_projects:judging_instance_detail", args=(self.judging_instance.pk,)
        )

    def get(self, request, *args, **kwargs):
        response = super().get(request, *args, **kwargs)
        self.judging_instance.set_locked()
        return response

    def post(self, request, *args, **kwargs):
        if "submit" in request.POST:
            self.submit = True
        else:
            self.submit = False
        return super(JudgingInstanceUpdate, self).post(request, *args, **kwargs)


class TeacherDetail(SpecificUserRequiredMixin, ListView):
    allow_superuser = True
    allow_staff = True
    template_name = "fair_projects/teacher_detail.html"
    context_object_name = "project_list"

    def get_required_user(self, *args, **kwargs):
        return get_object_or_404(User, username=kwargs["username"])

    def get_queryset(self):
        self.teacher = get_object_or_404(
            Teacher, user__username=self.kwargs["username"]
        )
        return (
            Project.objects.filter(student__teacher=self.teacher)
            .select_related("category", "subcategory", "division")
            .order_by("number")
        )

    def get_context_data(self, **kwargs):
        context = super(TeacherDetail, self).get_context_data(**kwargs)
        context["teacher"] = self.teacher

        request_user = self.request.user
        context["allow_create"] = False
        if request_user.is_authenticated:
            if request_user.has_perm("fair_projects.add_project"):
                context["allow_create"] = True
        return context


class StudentFeedbackForm(SpecificUserRequiredMixin, DetailView):
    allow_staff = True
    allow_superuser = True
    template_name = "fair_projects/student_feedback.html"
    model = Project
    context_object_name = "project"
    queryset = Project.objects.select_related("category", "subcategory", "division")
    feedback_template = "fair_projects/student_feedback_common_2.html"

    def get_required_user(self, *args, **kwargs):
        student = get_object_or_404(Student, pk=kwargs["student_id"])
        return student.teacher.user

    def get_object(self, queryset=None):
        if not queryset:
            queryset = self.queryset

        try:
            return queryset.get(number=self.kwargs["project_number"])
        except ObjectDoesNotExist:
            raise Http404()

    def get_context_data(self, **kwargs):
        context = super(StudentFeedbackForm, self).get_context_data(**kwargs)
        context["student"] = Student.objects.get(pk=self.kwargs["student_id"])
        context["project"] = context["student"].project
        context["questions"] = get_question_feedback_dict(context["project"])
        context["feedback_template"] = self.feedback_template

        return context


class TeacherStudentsFeedbackForm(SpecificUserRequiredMixin, ListView):
    allow_superuser = True
    allow_staff = True
    model = Student
    template_name = "fair_projects/student_feedback_multi.html"
    context_object_name = "student_list"
    feedback_template = "fair_projects/student_feedback_common_2.html"

    def get_required_user(self, *args, **kwargs):
        return get_object_or_404(User, username=kwargs["username"])

    def get_queryset(self):
        self.teacher = get_object_or_404(
            Teacher, user__username=self.kwargs["username"]
        )
        return (
            Student.objects.filter(teacher=self.teacher, project__isnull=False)
            .select_related("project")
            .order_by("last_name", "first_name")
        )

    def get_context_data(self, **kwargs):
        context = super(TeacherStudentsFeedbackForm, self).get_context_data(**kwargs)
        context["teacher"] = self.teacher

        Feedback = namedtuple("Feedback", ("student", "project", "questions"))
        feedback_list = []
        for student in context["student_list"]:
            feedback_list.append(
                Feedback(
                    student,
                    student.project,
                    get_question_feedback_dict(student.project),
                )
            )
        context["feedback_list"] = feedback_list
        context["feedback_template"] = self.feedback_template

        return context
