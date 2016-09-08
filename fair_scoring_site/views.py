from django.core.urlresolvers import reverse
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect


@login_required
def profile(request):
    if request.user.is_authenticated():
        if request.user.is_superuser:
            return HttpResponseRedirect(reverse('admin:index'))
        elif request.user.has_perm('judges.is_judge'):
            return HttpResponseRedirect(reverse('fair_projects:judge_detail',
                                                args=[request.user.username]))
        else:
            return HttpResponseRedirect(reverse('fair_projects:index'))
    else:
        return HttpResponseRedirect(reverse('fair_projects:index'))

def home(request):
    return HttpResponseRedirect(reverse('fair_projects:index'))