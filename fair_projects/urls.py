from django.conf.urls import url

from . import views

app_name = 'fair_projects'
urlpatterns = [
    url(r'^$', views.index, name='index'),
    url(r'^(?P<project_number>[0-9]+)/?$', views.detail, name='detail'),
    url(r'^judge/(?P<judge_username>[A-Za-z._0-9]+)/?$', views.judge_detail, name='judge_detail'),
    url(r'^judgingresponse/(?P<judginginstance_key>[0-9]+)/?$',
        views.judging_instance_detail, name='judging_instance_detail')
]