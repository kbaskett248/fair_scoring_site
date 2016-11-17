from abc import ABC, abstractclassmethod

from django.db import models


# Create your models here.
class Award(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    award_order = models.PositiveSmallIntegerField(blank=True, default=32767)
    award_count = models.PositiveIntegerField(default=1)
    percentage_count = models.BooleanField(default=False)
    exclude_awards = models.ManyToManyField('self', symmetrical=True)

    def __str__(self) -> str:
        return self.name

    def assign(self, instances, award_attr='awards'):
        exclude_awards = set(self.exclude_awards.all())
        for instance in instances:
            if set(getattr(instance, award_attr, set())) & exclude_awards:
                continue

            if self.instance_passes_all_rules(instance):
                getattr(instance, award_attr).append(self)
                return

    def instance_passes_all_rules(self, instance):
        for rule in self.awardrule_set.all():
            if not rule.allow_instance(instance):
                return False

        return True


class Operator(ABC):
    internal = None
    display = None

    @abstractclassmethod
    def operate(cls, value1, value2):
        pass


class In(Operator):
    internal = 'IN'
    display = 'in'

    @classmethod
    def operate(cls, value1, value2):
        if not value2:
            return False
        value_2_list = value2.split(',')
        return str(value1) in value_2_list


class NotIn(Operator):
    internal = 'NOT_IN'
    display = 'not in'

    @classmethod
    def operate(cls, value1, value2):
        if not value2:
            return True
        value_2_list = value2.split(',')
        return str(value1) not in value_2_list


class Is(Operator):
    internal = 'IS'
    display = 'is'

    @classmethod
    def operate(cls, value1, value2):
        return value1 == value2


class IsNot(Operator):
    internal = 'IS_NOT'
    display = 'is not'

    @classmethod
    def operate(cls, value1, value2):
        return value1 != value2


class Greater(Operator):
    internal = 'GREATER'
    display = 'is greater than'

    @classmethod
    def operate(cls, value1, value2):
        try:
            return float(value1) > float(value2)
        except ValueError:
            return value1 > value2


class Less(Operator):
    internal = 'LESS'
    display = 'is less than'

    @classmethod
    def operate(cls, value1, value2):
        try:
            return float(value1) < float(value2)
        except ValueError:
            return value1 < value2


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
    def operator(self) -> Operator:
        if (not self._operator) or (self.operator_name != self._operator.internal):
            self.set_operator()
        return self._operator

    @operator.setter
    def operator(self, value: Operator):
        self._operator = value
        self.operator_name = self._operator.internal

    def set_operator(self):
        if not self.operator_name:
            raise ValueError('operator_name is not set')

        for op in self.OPERATORS:
            if self.operator_name == op.internal:
                self._operator = op
                break
        else:
            raise ValueError('%s is not a valid operator. Must be one of %s' % (self.operator_name, self.OPERATORS))

    def allow_instance(self, instance) -> bool:
        instance_value = str(getattr(instance, self.trait))
        return self.operator.operate(instance_value, self.value)



