from django.conf.urls import url

from . import views

app_name = 'fair_projects'
urlpatterns = [
    url(r'^$', views.index, name='index'),
    url(r'^(?P<project_number>[0-9]+)/?$', views.ProjectDetail.as_view(), name='detail'),
    url(r'^judge/(?P<judge_username>[A-Za-z._0-9]+)/?$', views.JudgeDetail.as_view(), name='judge_detail'),
    url(r'^judgingresponse/(?P<judginginstance_key>[0-9]+)/?$',
        views.JudgingInstanceDetail.as_view(), name='judging_instance_detail'),
    url(r'^judgingresponse/(?P<judginginstance_key>[0-9]+)/edit/?$',
        views.JudgingInstanceUpdate.as_view(), name='judging_instance_edit'),
    url(r'^teacher/(?P<username>[A-Za-z._0-9]+)/?', views.TeacherDetail.as_view(), name='teacher_detail')
]