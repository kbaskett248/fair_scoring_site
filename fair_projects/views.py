import functools
import logging
from collections import defaultdict

from django.contrib.auth.mixins import AccessMixin, PermissionRequiredMixin
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.core.urlresolvers import reverse
from django.http import Http404
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render, get_object_or_404
from django.views.decorators.csrf import csrf_protect
from django.views.generic import DetailView, ListView
from django.views.generic.edit import UpdateView, CreateView

from .forms import UploadFileForm
from .logic import handle_project_import
from .models import Project, Student, JudgingInstance, Teacher
from judges.models import Judge
from rubrics.models import Question
from rubrics.forms import rubric_form_factory

logger = logging.getLogger(__name__)


class ProjectIndex(ListView):
    template_name = 'fair_projects/index.html'
    model = Project
    queryset = Project.objects.select_related('category', 'subcategory', 'division')\
        .order_by('number', 'title')
    context_object_name = 'project_list'

    def get_context_data(self, **kwargs):
        context = super(ProjectIndex, self).get_context_data(**kwargs)

        request_user = self.request.user
        context['allow_create'] = False
        if request_user.is_authenticated():
            if request_user.has_perm('fair_projects.add_project'):
                context['allow_create'] = True

        return context


class ProjectCreate(PermissionRequiredMixin, CreateView):
    model = Project
    template_name = 'fair_projects/project_create.html'
    fields = ('title', 'category', 'subcategory', 'division')
    permission_required = 'fair_projects.add_project'

    def get_success_url(self):
        return reverse('fair_projects:detail', args=(self.object.number, ))


class ProjectDetail(DetailView):
    template_name = 'fair_projects/detail.html'
    model = Project
    context_object_name = 'project'
    queryset = Project.objects.select_related(
        'category', 'subcategory', 'division')

    def get_object(self, queryset=None):
        if not queryset:
            queryset = self.queryset

        try:
            return queryset.get(number=self.kwargs['project_number'])
        except ObjectDoesNotExist:
            raise Http404()

    def get_context_data(self, **kwargs):
        context = super(ProjectDetail, self).get_context_data(**kwargs)

        context['student_list'] = Student.objects.filter(project=self.object)
        judge_instances = JudgingInstance.objects.filter(project=self.object)
        context['judge_list'] = [ji.judge for ji in judge_instances]

        request_user = self.request.user
        context['is_submitting_teacher'] = False
        if request_user.is_authenticated():
            if request_user.is_superuser:
                context['is_submitting_teacher'] = True
            elif request_user.has_perm('fair_projects.is_teacher'):
                teacher = Teacher.objects.get(user=request_user)
                if [student for student in context['student_list']
                        if student.teacher == teacher]:
                    context['is_submitting_teacher'] = True

        return context


def judge_assignment(request):
    num_deleted = JudgingInstance.objects.all().delete()
    added = []
    for proj in Project.objects.all():
        for judge in Judge.objects.all():
            ji = JudgingInstance(judge=judge, project=proj)
            ji.save()
            added.append('Judge: {0}    Project: {1}'.format(judge, proj))
    return HttpResponse(
        "Assigning Judges<br />{0}<br />{1}".format(
            str(num_deleted), "<br />".join(added)))


@csrf_protect
def import_projects(request):
    logger.info('Import Projects; request=%s', request)
    c = {}
    if request.method == 'POST':
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            handle_project_import(request.FILES['file'])
            return HttpResponseRedirect('/admin/fair_projects/project/')
    else:
        form = UploadFileForm()

    request.current_app = 'fair_projects'
    c.update({'form': form})
    return render(request, 'fair_projects/project_upload.html', c)


class SpecificUserRequiredMixin(AccessMixin):
    allow_superuser = False

    def get_required_user(self, *args, **kwargs):
        raise NotImplementedError(
            '{0} is missing the implementation of the get_user_from_path() method.'.format(self.__class__.__name__)
        )

    def dispatch(self, request, *args, **kwargs):
        current_user = self.request.user
        required_user = self.get_required_user(*args, **kwargs)

        if not current_user.is_authenticated():
            return self.handle_no_permission()

        if self.allow_superuser and current_user.is_superuser:
            return super(SpecificUserRequiredMixin, self).dispatch(request, *args, **kwargs)

        if current_user != required_user:
            return self.handle_no_permission()

        return super(SpecificUserRequiredMixin, self).dispatch(request, *args, **kwargs)


class JudgeDetail(SpecificUserRequiredMixin, ListView):
    allow_superuser = True
    template_name = 'fair_projects/judge_detail.html'
    context_object_name = 'judginginstance_list'

    def get_required_user(self, *args, **kwargs):
        return get_object_or_404(User, username=kwargs['judge_username'])

    def get_queryset(self):
        self.judge = get_object_or_404(Judge, user__username=self.kwargs['judge_username'])
        return JudgingInstance.objects.filter(judge=self.judge,
                                              response__rubric__name="Judging Form") \
            .order_by('project__number') \
            .select_related('project', 'project__category', 'project__division')

    def get_context_data(self, **kwargs):
        context = super(JudgeDetail, self).get_context_data(**kwargs)
        context['judge'] = self.judge
        return context


class JudgingInstanceMixin(SpecificUserRequiredMixin):
    allow_superuser = True
    template_name = 'fair_projects/judging_instance_detail.html'
    pk_url_kwarg = 'judginginstance_key'
    model = JudgingInstance
    queryset = JudgingInstance.objects.select_related(
        'judge', 'project', 'response', 'judge__user')
    context_object_name = 'judging_instance'

    def get_required_user(self, *args, **kwargs):
        self.judging_instance = self.queryset.get(pk=kwargs[self.pk_url_kwarg])
        self.judge = self.judging_instance.judge
        user_name = self.judge.user.username
        return get_object_or_404(User, username=user_name)

    def get_context_data(self, **kwargs):
        context = super(JudgingInstanceMixin, self).get_context_data(**kwargs)

        context['judge'] = self.judge
        project = self.judging_instance.project
        context['project'] = project
        context['student_list'] = project.student_set.all()
        context['rubric_response'] = self.judging_instance.response
        context['edit_mode'] = False

        return context


class JudgingInstanceDetail(JudgingInstanceMixin, DetailView):
    template_dict = {Question.MULTI_SELECT_TYPE: 'rubrics/multi_select_type_view.html',
                     Question.LONG_TEXT: 'rubrics/long_text_type_view.html'}
    default_template = 'rubrics/default_type_view.html'

    def get_context_data(self, **kwargs):
        context = super(JudgingInstanceDetail, self).get_context_data(**kwargs)
        template_dict = defaultdict(functools.partial(self.get_default_template, **kwargs))
        template_dict.update(self.get_template_dict(**kwargs))
        question_list = [(template_dict[question_type], question, answer)
                         for question_type, question, answer
                         in context['rubric_response'].question_answer_iter()]
        context['question_list'] = question_list

        return context

    def get_template_dict(self, **kwargs):
        return self.template_dict

    def get_default_template(self, **kwargs):
        return self.default_template


class JudgingInstanceUpdate(JudgingInstanceMixin, UpdateView):
    def get_context_data(self, **kwargs):
        context = super(JudgingInstanceUpdate, self).get_context_data(**kwargs)

        context['edit_mode'] = True
        context['post_url'] = reverse('fair_projects:judging_instance_edit',
                                      args=(self.judging_instance.pk,))
        context['rubric_form'] = context['form']

        return context

    def get_form_class(self):
        return rubric_form_factory(self.object.response.rubric)

    def get_form_kwargs(self):
        kwargs = super(JudgingInstanceUpdate, self).get_form_kwargs()
        kwargs['instance'] = kwargs['instance'].response
        if 'data' not in kwargs:
            kwargs['data'] = kwargs['instance'].get_form_data()
        return kwargs

    def get_success_url(self):
        return reverse('fair_projects:judging_instance_detail',
                       args=(self.object.pk,))


class TeacherDetail(SpecificUserRequiredMixin, ListView):
    allow_superuser = True
    template_name = 'fair_projects/teacher_detail.html'
    context_object_name = 'project_list'

    def get_required_user(self, *args, **kwargs):
        return get_object_or_404(User, username=kwargs['username'])

    def get_queryset(self):
        self.teacher = get_object_or_404(Teacher, user__username=self.kwargs['username'])
        return Project.objects.filter(student__teacher=self.teacher)\
            .select_related('category', 'subcategory', 'division')\
            .order_by('number')

    def get_context_data(self, **kwargs):
        context = super(TeacherDetail, self).get_context_data(**kwargs)
        context['teacher'] = self.teacher
        return context
