import logging

from django.http import HttpResponse, Http404, HttpResponseRedirect
from django.shortcuts import render, get_object_or_404
from django.views.decorators.csrf import csrf_protect

from .forms import UploadFileForm
from .logic import handle_project_import
from .models import Project, Student, JudgingInstance
from fair_categories.models import Division, Category, Subcategory
from judges.models import Judge


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

def judge_detail(request, judge_id):
    judge = get_object_or_404(Judge, pk=judge_id)
    judge_instances = JudgingInstance.objects.filter(judge=judge)
    project_list = [ji.project for ji in judge_instances]

    return render(request, 'fair_projects/judge_detail.html',
                  { 'judge': judge,
                    'project_list': project_list }
                  )

@csrf_protect
def import_projects(request):
    logger.info('Import Projects; request=%s', request)
    c = {}
    if request.method == 'POST':
        form = UploadFileForm(request.POST, request.FILES)
        logger.info('%s', form)
        logger.info('&s', request.FILES)
        if form.is_valid():
            handle_project_import(request.FILES['file'])
            return HttpResponseRedirect('/admin/fair_projects/project/')
    else:
        form = UploadFileForm()
    c.update({'form': form})
    return render(request, 'fair_projects/project_upload.html', c)
