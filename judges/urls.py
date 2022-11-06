from django.conf.urls import url

from . import views

app_name = "judges"
urlpatterns = [url(r"^signup/?$", views.JudgeCreateView.as_view(), name="judge_create")]
