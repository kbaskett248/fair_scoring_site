import itertools
from django.db import models
from django.contrib.auth.models import User

from fair_categories.models import Ethnicity, Category, Subcategory, Division
from judges.models import Judge
from rubrics.models import RubricResponse


class School(models.Model):
    name = models.CharField(
        max_length=200)

    def __str__(self):
        return self.name


# Create your models here.
class Teacher(models.Model):
    user = models.OneToOneField(User,
                                on_delete=models.CASCADE,
                                primary_key=True)
    school = models.ForeignKey(
        School,
        on_delete=models.PROTECT
    )

    class Meta:
        permissions = (
            ('is_teacher', 'Designate this user as a teacher'),
        )

    def __str__(self):
        return self.user.first_name + ' ' + self.user.last_name


class Student(models.Model):
    GENDER_FEMALE = 'F'
    GENDER_MALE = 'M'
    GENDER_CHOICES = (
        (GENDER_FEMALE, 'Female'),
        (GENDER_MALE, 'Male')
    )

    first_name = models.CharField(
        max_length=50)
    last_name = models.CharField(
        max_length=50)
    ethnicity = models.ForeignKey(
        Ethnicity,
        on_delete=models.PROTECT
    )
    gender = models.CharField(
        max_length=1,
        choices=GENDER_CHOICES
    )
    teacher = models.ForeignKey(
        Teacher,
        on_delete=models.PROTECT
    )
    grade_level = models.PositiveSmallIntegerField()
    email = models.EmailField(null=True)
    project = models.ForeignKey(
        'Project',
        on_delete=models.SET_NULL,
        null=True
    )

    def __str__(self):
        return self.first_name + ' ' + self.last_name


class Project(models.Model):
    title = models.CharField(max_length=65)
    abstract = models.TextField(blank=True)
    number = models.CharField(max_length=5, blank=True)
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT
    )
    subcategory = models.ForeignKey(
        Subcategory,
        on_delete=models.PROTECT
    )
    division = models.ForeignKey(
        Division,
        on_delete=models.PROTECT
    )

    # def __init__(self, *args, **kwargs):
    #     # __init__ is run when objects are retrieved from the database
    #     # in addition to when they are created.
    #     super(Project, self).__init__(*args, **kwargs)
    #     if not self.number:
    #         self.number = self.get_next_number()
    #         self.save()

    def get_next_number(self):
        max_proj_num = Project.objects.filter(
            division=self.division, category=self.category).aggregate(models.Max('number'))['number__max']
        if max_proj_num:
            return int(max_proj_num) + 1
        else:
            categories = sorted(Category.objects.all(), key=lambda x: x.short_description)
            divisions = sorted(Division.objects.all(), key=lambda x: x.short_description)
            default_min = 0
            for div, cat in itertools.product(divisions, categories):
                default_min += 1000
                if div == self.division and cat == self.category:
                    return default_min + 1

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        if not self.number:
            self.number = self.get_next_number()
        return super(Project, self).save(force_insert, force_update, using,
                                         update_fields)

    def __str__(self):
        return self.title


class JudgingInstance(models.Model):
    judge = models.ForeignKey(
        Judge,
        models.CASCADE
    )
    project = models.ForeignKey(
        Project,
        models.CASCADE
    )
    response = models.ForeignKey(
        'rubrics.RubricResponse',
        models.CASCADE,
        null=True, blank=True
    )

    def __init__(self, *args, **kwargs):
        rubric = kwargs.pop('rubric', None)
        super(JudgingInstance, self).__init__(*args, **kwargs)
        if not self.response and rubric:
            self.response = RubricResponse.objects.create(rubric=rubric)

    def __str__(self):
        return '{0} - {1}: {2}'.format(self.judge, self.project, self.response.rubric.name)
