from abc import ABC

from django.db import models


# Create your models here.
class Award(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    award_order = models.PositiveSmallIntegerField(blank=True, default=32767)
    award_count = models.PositiveIntegerField(default=1)
    percentage_count = models.BooleanField(default=False)
    exclude_awards = models.ManyToManyField('self', symmetrical=True)

    def __str__(self):
        return self.name


class Operator(ABC):
    internal = None
    display = None


class In(Operator):
    internal = 'IN'
    display = 'in'


class NotIn(Operator):
    internal = 'NOT_IN'
    display = 'not in'


class Is(Operator):
    internal = 'IS'
    display = 'is'


class IsNot(Operator):
    internal = 'IS_NOT'
    display = 'is not'


class Greater(Operator):
    internal = 'GREATER'
    display = 'is greater than'


class Less(Operator):
    internal = 'LESS'
    display = 'is less than'


class AwardRule(models.Model):
    OPERATORS = (Is, IsNot, Greater, Less, In, NotIn)
    OPERATOR_CHOICES = tuple([(op.internal, op.display) for op in OPERATORS])

    award = models.ForeignKey(Award, on_delete=models.CASCADE)
    trait = models.CharField(max_length=50)
    operator_name = models.CharField(max_length=20, choices=OPERATOR_CHOICES)
    value = models.CharField(max_length=300)

    def __init__(self, *args, **kwargs):
        super(AwardRule, self).__init__(*args, **kwargs)
        self._operator = None
        self.set_operator()

    def __str__(self):
        return '{0} {1} {2}'.format(self.trait, self.operator.display, self.value)

    @property
    def operator(self):
        if (not self._operator) or (self.operator_name != self._operator.internal):
            self.set_operator()
        return self._operator

    def set_operator(self):
        if not self.operator_name:
            raise ValueError('operator_name is not set')

        for op in self.OPERATORS:
            if self.operator_name == op.internal:
                self._operator = op()
                break
        else:
            raise ValueError('%s is not a valid operator. Must be one of %s' % (self.operator_name, self.OPERATORS))



