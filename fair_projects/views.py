import logging

from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.mixins import UserPassesTestMixin
from django.core.urlresolvers import reverse
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render, get_object_or_404
from django.views.decorators.csrf import csrf_protect
from django.views.generic.base import TemplateView

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


# def judge_detail(request, judge_username):
#     judge = get_object_or_404(Judge, user__username=judge_username)
#     judge_instances = JudgingInstance.objects.filter(judge=judge, response__rubric__name="Judging Form")\
#         .order_by('project__number')\
#         .select_related('project', 'project__category', 'project__division')
#
#     return render(request, 'fair_projects/judge_detail.html',
#                   { 'judge': judge,
#                     'judginginstance_list': judge_instances }
#                   )


@login_required
@permission_required('judges.is_judge')
def judging_instance_detail(request, judginginstance_key):
    judging_instance = JudgingInstance.objects\
        .select_related('judge', 'project', 'response') \
        .get(pk=judginginstance_key)
    project = judging_instance.project
    context = {'judge': judging_instance.judge,
               'project': project,
               'student_list': project.student_set.all(),
               'rubric_response': judging_instance.response,
               'judging_instance': judging_instance}
    if request.path == reverse('fair_projects:judging_instance_edit', args=[judginginstance_key]):
        context['rubric_form'] = RubricForm(judging_instance.response.rubric)

    return render(request, 'fair_projects/judging_instance_detail.html',
                  context)


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


class SpecificUserRequiredMixin(UserPassesTestMixin):

    def test_func(self):
        current_user = self.request.user
        if not current_user.is_authenticated():
            return False

        required_user = self.get_user()
        if current_user is not required_user:
            return False

        return super(SpecificUserRequiredMixin, self).test_func()

    def get_user(self):
        raise NotImplementedError(
            '{0} is missing the implementation of the get_user_from_path() method.'.format(self.__class__.__name__)
        )


class JudgeDetail(SpecificUserRequiredMixin, TemplateView):

    template_name = 'fair_projects/judge_detail.html'

    def __init__(self, *args, **kwargs):
        super(JudgeDetail, self).__init__()
        self.judge = get_object_or_404(Judge, user__username=self.judge_username)

    def get_user(self):
        return self.judge.user

    def get_context_data(self, **kwargs):
        context = super(JudgeDetail, self).get_context_data(**kwargs)
        context['judge'] = self.judge
        context['judginginstance_list'] = JudgingInstance.objects.filter(judge=self.judge,
                                                                         response__rubric__name="Judging Form") \
            .order_by('project__number') \
            .select_related('project', 'project__category', 'project__division')

        return context

