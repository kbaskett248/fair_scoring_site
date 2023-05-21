from django.urls import re_path

from . import views

app_name = "judges"  # pylint: disable=C0103
urlpatterns = [
    re_path(r"^signup/?$", views.JudgeCreateView.as_view(), name="judge_create")
]
