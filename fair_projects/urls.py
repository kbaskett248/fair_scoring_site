from django.conf.urls import url

from . import views

app_name = 'fair_projects'
urlpatterns = [
    url(r'^$', views.index, name='index'),
    url(r'^(?P<project_number>[0-9]+)/?$', views.detail, name='detail'),
    url(r'^judge/(?P<judge_username>[A-Za-z._0-9]+)/?$', views.judge_detail, name='judge_detail'),
]