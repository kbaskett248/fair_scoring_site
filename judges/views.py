from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.views.generic.edit import CreateView

from judges.models import Judge


class JudgeCreateView(CreateView):
    """The summary line for a class docstring should fit on one line.

    If the class has public attributes, they may be documented here
    in an ``Attributes`` section and follow the same formatting as a
    function's ``Args`` section. Alternatively, attributes may be documented
    inline with the attribute's declaration (see __init__ method below).

    Properties created with the ``@property`` decorator should be documented
    in the property's getter method.

    Attributes:
        attr1 (str): Description of `attr1`.
        attr2 (:obj:`int`, optional): Description of `attr2`.

    """

    model = Judge
    template_name = 'judges/judge_create.html'
    fields = ['user',
              'phone',
              'has_device',
              'education',
              'fair_experience',
              'categories',
              'divisions',
              ]


