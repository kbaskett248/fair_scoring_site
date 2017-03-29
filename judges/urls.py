from django.conf.urls import url

from . import views

app_name = 'fair_projects'
urlpatterns = [
    url(r'^signup/?$', views.JudgeCreateView.as_view(), name='judge_create')
]