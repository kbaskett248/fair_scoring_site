from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect
from django.urls import reverse


@login_required
def profile(request):
    if request.user.is_authenticated:
        if request.user.is_superuser:
            return HttpResponseRedirect(reverse("admin:index"))
        elif request.user.has_perm("judges.is_judge"):
            return HttpResponseRedirect(
                reverse("fair_projects:judge_detail", args=[request.user.username])
            )
        elif request.user.has_perm("fair_projects.is_teacher"):
            return HttpResponseRedirect(
                reverse("fair_projects:teacher_detail", args=(request.user.username,))
            )
        else:
            return HttpResponseRedirect(reverse("fair_projects:index"))
    else:
        return HttpResponseRedirect(reverse("fair_projects:index"))


def home(request):
    return HttpResponseRedirect(reverse("fair_projects:index"))
