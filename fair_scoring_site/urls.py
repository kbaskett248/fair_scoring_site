"""fair_scoring_site URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.9/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
import django.contrib.admin
from django.conf import settings
from django.conf.urls import url, include

from fair_projects.views import import_projects, judge_assignment, notify_teachers, delete_judge_assignments
from . import admin  # This is needed to load the Awards admin
from .views import *

urlpatterns = [
    # url(r'^admin/fair_projects/project/import', import_projects, name='import_projects'),
    url(r'^admin/fair_projects/project/assign', judge_assignment, name='assign_projects'),
    url(r'^admin/fair_projects/project/delete', delete_judge_assignments, name='delete_instances'),
    url(r'^admin/auth/user/teacher-notify', notify_teachers, name='teacher_notify'),
    url(r'^admin/', django.contrib.admin.site.urls),
    url(r'^accounts/profile/', profile, name='profile'),
    url(r'^accounts/', include('django.contrib.auth.urls')),
    url(r'^$', home, name='home'),
    url(r'^projects/', include('fair_projects.urls')),
    url(r'^judges/', include('judges.urls'))
]

if settings.DEBUG:
    import debug_toolbar
    urlpatterns = [
        url(r'^__debug__/', include(debug_toolbar.urls)),
    ] + urlpatterns
