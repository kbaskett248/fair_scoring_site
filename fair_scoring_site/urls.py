"""fair_scoring_site re_path Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.9/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a re_path to urlpatterns:  re_path(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a re_path to urlpatterns:  re_path(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import re_path, include
    2. Add a re_path to urlpatterns:  re_path(r'^blog/', include('blog.urls'))
"""
import django.contrib.admin
from django.conf import settings
from django.urls import include, re_path

from apps.fair_projects.views import (
    delete_judge_assignments,
    judge_assignment,
    notify_teachers,
)

# We need to load the admin and signals here, otherwise they will not be loaded
from . import admin  # noqa: F401
from . import signals  # noqa: F401
from .views import home, profile

urlpatterns = [
    re_path(
        r"^admin/fair_projects/project/assign", judge_assignment, name="assign_projects"
    ),
    re_path(
        r"^admin/fair_projects/project/delete",
        delete_judge_assignments,
        name="delete_instances",
    ),
    re_path(r"^admin/auth/user/teacher-notify", notify_teachers, name="teacher_notify"),
    re_path(r"^admin/", django.contrib.admin.site.urls),
    re_path(r"^accounts/profile/", profile, name="profile"),
    re_path(r"^accounts/", include("django.contrib.auth.urls")),
    re_path(r"^$", home, name="home"),
    re_path(r"^projects/", include("apps.fair_projects.urls")),
    re_path(r"^judges/", include("apps.judges.urls")),
]

if settings.DEBUG:
    import debug_toolbar

    urlpatterns = [
        re_path(r"^__debug__/", include(debug_toolbar.urls)),
    ] + urlpatterns
