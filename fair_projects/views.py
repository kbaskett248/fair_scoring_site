import logging

from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.mixins import AccessMixin
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.core.urlresolvers import reverse
from django.http import Http404
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render, get_object_or_404
from django.views.decorators.csrf import csrf_protect
from django.views.generic import DetailView, ListView

from judges.models import Judge
from .forms import UploadFileForm
from .logic import handle_project_import
from .models import Project, Student, JudgingInstance
from rubrics.forms import RubricForm


logger = logging.getLogger(__name__)


def index(request):
    project_list = Project.objects.order_by('number', 'title')
    context = { 'project_list': project_list }
    return render(request, 'fair_projects/index.html', context)

def detail(request, project_number):
    project = get_object_or_404(Project, number=project_number)
    student_list = Student.objects.filter(project=project)
    judge_instances = JudgingInstance.objects.filter(project=project)
    judge_list = [ji.judge for ji in judge_instances]

    return render(request, 'fair_projects/detail.html',
                  { 'project': project,
                    'student_list': student_list,
                    'judge_list': judge_list,
                  })


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


class JudgingInstanceDetail(SpecificUserRequiredMixin, DetailView):
    allow_superuser = True
    template_name = 'fair_projects/judging_instance_detail.html'
    pk_url_kwarg = 'judginginstance_key'
    model = JudgingInstance
    queryset = JudgingInstance.objects.select_related(
        'judge', 'project', 'response', 'judge__user')
    context_object_name = 'judging_instance'

    def get_required_user(self, *args, **kwargs):
        self.judging_instance = self.get_object()
        self.judge = self.judging_instance.judge
        user_name = self.judge.user.username
        return get_object_or_404(User, username=user_name)

    def get_object(self, queryset=None):
        return super(JudgingInstanceDetail, self).get_object(queryset)

    def get_context_data(self, **kwargs):
        context = super(JudgingInstanceDetail, self).get_context_data(**kwargs)

        context['judge'] = self.judge
        project = self.judging_instance.project
        context['project'] = project
        context['student_list'] = project.student_set.all()
        context['rubric_response'] = self.judging_instance.response
        context['edit_mode'] = self.kwargs['edit_mode']
        if self.kwargs['edit_mode']:
            context['post_url'] = reverse('fair_projects:judging_instance_detail',
                                          args=(self.judging_instance.pk, True))
            if self.request.method == 'POST':
                form = RubricForm(self.judging_instance.response, data=self.request.POST)
            else:
                form = RubricForm(self.judging_instance.response)
            context['rubric_form'] = form

        return context

    def post(self, request, *args, **kwargs):
        return 'We posted'

