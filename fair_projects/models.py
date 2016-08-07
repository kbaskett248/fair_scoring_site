from django.db import models
from django.contrib.auth.models import User

from fair_categories.models import Ethnicity, Category, Subcategory, Division
from judges.models import Judge


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
        on_delete=models.PROTECT
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




