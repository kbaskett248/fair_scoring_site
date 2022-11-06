from django.urls import re_path

from . import views

app_name = "fair_projects"
urlpatterns = [
    re_path(r"^$", views.ProjectIndex.as_view(), name="index"),
    re_path(r"^create/?$", views.ProjectCreate.as_view(), name="project_create"),
    re_path(
        r"^(?P<project_number>[0-9]+)/?$", views.ProjectDetail.as_view(), name="detail"
    ),
    re_path(
        r"^(?P<project_number>[0-9]+)/update/?$",
        views.ProjectUpdate.as_view(),
        name="project_update",
    ),
    re_path(
        r"^(?P<project_number>[0-9]+)/delete/?$",
        views.ProjectDelete.as_view(),
        name="project_delete",
    ),
    re_path(
        r"^(?P<project_number>[0-9]+)/feedback/student/(?P<student_id>[0-9]+)/?$",
        views.StudentFeedbackForm.as_view(),
        name="student_feedback_form",
    ),
    re_path(r"^judges/?$", views.JudgeIndex.as_view(), name="judge_index"),
    re_path(
        r"^judge/(?P<judge_username>[-+@._A-Za-z0-9]+)/?$",
        views.JudgeDetail.as_view(),
        name="judge_detail",
    ),
    re_path(
        r"^judgingresponse/(?P<judginginstance_key>[0-9]+)/?$",
        views.JudgingInstanceDetail.as_view(),
        name="judging_instance_detail",
    ),
    re_path(
        r"^judgingresponse/(?P<judginginstance_key>[0-9]+)/edit/?$",
        views.JudgingInstanceUpdate.as_view(),
        name="judging_instance_edit",
    ),
    re_path(
        r"^teacher/(?P<username>[-+@._A-Za-z0-9]+)/?$",
        views.TeacherDetail.as_view(),
        name="teacher_detail",
    ),
    re_path(
        r"^teacher/(?P<username>[-+@._A-Za-z0-9]+)/feedback/?$",
        views.TeacherStudentsFeedbackForm.as_view(),
        name="teacher_feedback",
    ),
    re_path(r"^results/?$", views.ResultsIndex.as_view(), name="project_results"),
]
