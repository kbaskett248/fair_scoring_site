from django.conf.urls import url

from . import views

app_name = 'fair_projects'
urlpatterns = [
    url(r'^$', views.ProjectIndex.as_view(), name='index'),
    url(r'^create/?$', views.ProjectCreate.as_view(), name='project_create'),
    url(r'^(?P<project_number>[0-9]+)/?$', views.ProjectDetail.as_view(), name='detail'),
    url(r'^(?P<project_number>[0-9]+)/update/?$', views.ProjectUpdate.as_view(), name='project_update'),
    url(r'^(?P<project_number>[0-9]+)/delete/?$', views.ProjectDelete.as_view(), name='project_delete'),
    url(r'^(?P<project_number>[0-9]+)/feedback/(?P<student_id>[0-9]+)/?$', views.myview, name='student_feedback_form'),
    url(r'^judge/(?P<judge_username>[A-Za-z._0-9]+)/?$', views.JudgeDetail.as_view(), name='judge_detail'),
    url(r'^judgingresponse/(?P<judginginstance_key>[0-9]+)/?$',
        views.JudgingInstanceDetail.as_view(), name='judging_instance_detail'),
    url(r'^judgingresponse/(?P<judginginstance_key>[0-9]+)/edit/?$',
        views.JudgingInstanceUpdate.as_view(), name='judging_instance_edit'),
    url(r'^teacher/(?P<username>[A-Za-z._0-9]+)/?', views.TeacherDetail.as_view(), name='teacher_detail'),
    url(r'^results/?$', views.ResultsIndex.as_view(), name='project_results')
]