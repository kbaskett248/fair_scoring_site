from abc import ABC, abstractmethod

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.db import models


# Create your models here.
class Award(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    award_order = models.PositiveSmallIntegerField(blank=True, default=32767)
    award_count = models.PositiveIntegerField(default=1)
    percentage_count = models.BooleanField(default=False)
    exclude_awards = models.ManyToManyField("self", symmetrical=True, blank=True)

    def __str__(self) -> str:
        return self.name

    def assign(self, instances):
        self.delete_award_instances()

        matching_instances = [
            instance
            for instance in instances
            if self.instance_passes_all_rules(instance)
        ]
        if not matching_instances:
            return

        exclude_awards = set(self.exclude_awards.all())
        num_to_assign = self.get_number_to_assign(len(matching_instances))

        for instance in matching_instances:
            if set(instance.get_awards()) & exclude_awards:
                continue

            instance.assign_award(self)
            num_to_assign -= 1

            if num_to_assign <= 0:
                return

    def is_valid_for_instance(self, instance):
        if self.exclude_from_instance(instance):
            return self.instance_passes_all_rules(instance)
        return False

    def instance_passes_all_rules(self, instance):
        for rule in self.awardrule_set.all():
            if not rule.allow_instance(instance):
                return False

        return True

    def exclude_from_instance(self, instance):
        return set(instance.get_awards()) & set(self.exclude_awards.all())

    def num_awards_str(self):
        if self.percentage_count:
            return f"{self.award_count}%"
        return str(self.award_count)

    num_awards_str.short_description = "Award Count"

    def get_number_to_assign(self, num_instances):
        if self.percentage_count:
            return round(num_instances * self.award_count / 100)

        return self.award_count

    def delete_award_instances(self):
        self.awardinstance_set.all().delete()

    @classmethod
    def get_awards_for_object(cls, object_):
        return AwardInstance.get_awards_for_object(object_)


class Operator(ABC):
    internal = None
    display = None

    @classmethod
    @abstractmethod
    def operate(cls, value1, value2) -> bool:
        pass


class In(Operator):
    internal = "IN"
    display = "in"

    @classmethod
    def operate(cls, value1, value2) -> bool:
        if not value2:
            return False
        value_2_list = str(value2).split(",")
        return str(value1) in value_2_list


class NotIn(Operator):
    internal = "NOT_IN"
    display = "not in"

    @classmethod
    def operate(cls, value1, value2) -> bool:
        if not value2:
            return True
        value_2_list = value2.split(",")
        return str(value1) not in value_2_list


class Is(Operator):
    internal = "IS"
    display = "is"

    @classmethod
    def operate(cls, value1, value2) -> bool:
        return str(value1) == str(value2)


class IsNot(Operator):
    internal = "IS_NOT"
    display = "is not"

    @classmethod
    def operate(cls, value1, value2) -> bool:
        return str(value1) != str(value2)


class Greater(Operator):
    internal = "GREATER"
    display = "is greater than"

    @classmethod
    def operate(cls, value1, value2) -> bool:
        if isinstance(value1, bool) or isinstance(value2, bool):
            return bool(value1) > bool(value2)
        try:
            return float(value1) > float(value2)
        except ValueError:
            return str(value1) > str(value2)


class Less(Operator):
    internal = "LESS"
    display = "is less than"

    @classmethod
    def operate(cls, value1, value2) -> bool:
        if isinstance(value1, bool) or isinstance(value2, bool):
            return bool(value1) < bool(value2)
        try:
            return float(value1) < float(value2)
        except ValueError:
            return str(value1) < str(value2)


class AwardRule(models.Model):
    OPERATORS = (Is, IsNot, Greater, Less, In, NotIn)
    OPERATOR_CHOICES = tuple((op.internal, op.display) for op in OPERATORS)

    award = models.ForeignKey(Award, on_delete=models.CASCADE)
    trait = models.CharField(max_length=50)
    operator_name = models.CharField(max_length=20, choices=OPERATOR_CHOICES)
    value = models.CharField(max_length=300)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._operator = None
        if self.operator_name:
            self.set_operator()

    def __str__(self):
        return f"{self.trait} {self.operator.display} {self.value}"

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
            raise ValueError("operator_name is not set")

        for op in self.OPERATORS:
            if self.operator_name == op.internal:
                self._operator = op
                break
        else:
            raise ValueError(
                f"{self.operator_name} is not a valid operator. "
                f"Must be one of {self.OPERATORS}"
            )

    def allow_instance(self, instance) -> bool:
        instance_value = getattr(instance, self.trait)
        return self.operator.operate(instance_value, self.value)


class AwardInstance(models.Model):
    award = models.ForeignKey(Award, on_delete=models.CASCADE)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.CharField(max_length=50)
    content_object = GenericForeignKey()

    def __str__(self):
        try:
            return f"{self.content_object} - {self.award}"
        except ObjectDoesNotExist:
            return self.content_object_str()

    def content_object_str(self):
        return str(self.content_object)

    content_object_str.short_description = "Item"

    @classmethod
    def get_award_instance_queryset_for_object(cls, object_):
        cont_type = ContentType.objects.get_for_model(object_)
        return (
            AwardInstance.objects.filter(content_type=cont_type, object_id=object_.pk)
            .select_related("award")
            .all()
        )

    @classmethod
    def get_award_instances_for_object(cls, object_):
        return list(cls.get_award_instance_queryset_for_object(object_))

    @classmethod
    def get_awards_for_object(cls, object_):
        return [
            instance.award
            for instance in cls.get_award_instance_queryset_for_object(object_)
        ]
