from django.urls import re_path

from . import views

app_name = "judges"
urlpatterns = [
    re_path(r"^signup/?$", views.JudgeCreateView.as_view(), name="judge_create")
]
