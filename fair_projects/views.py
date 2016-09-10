import logging

from django.contrib.auth.decorators import login_required, permission_required
from django.core.urlresolvers import reverse
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render, get_object_or_404
from django.views.decorators.csrf import csrf_protect

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


def judge_detail(request, judge_username):
    judge = get_object_or_404(Judge, user__username=judge_username)
    judge_instances = JudgingInstance.objects.filter(judge=judge, response__rubric__name="Judging Form")\
        .order_by('project__number')\
        .select_related('project', 'project__category', 'project__division')

    return render(request, 'fair_projects/judge_detail.html',
                  { 'judge': judge,
                    'judginginstance_list': judge_instances }
                  )


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
