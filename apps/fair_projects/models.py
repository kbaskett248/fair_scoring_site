from django.contrib.auth.models import Group, Permission, User
from django.core.exceptions import ObjectDoesNotExist
from django.core.management.color import Style
from django.db import models, transaction
from django.db.models import Manager, QuerySet
from django.urls.base import reverse

from apps.fair_categories.models import Category, Division, Ethnicity, Subcategory
from apps.fair_projects.utils import make_random_password
from apps.judges.models import Judge
from apps.rubrics.models.rubric import RubricResponse


class School(models.Model):
    name = models.CharField(max_length=200)

    def __str__(self):
        return self.name


class WithUserManager(Manager):
    def get_queryset(self):
        return super().get_queryset().select_related("user")


# Create your models here.
class Teacher(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    school = models.ForeignKey(School, on_delete=models.PROTECT)

    objects = WithUserManager()

    class Meta:
        permissions = (("is_teacher", "Designate this user as a teacher"),)
        ordering = ("user__last_name", "user__first_name")

    def __str__(self):
        return self.user.first_name + " " + self.user.last_name


@transaction.atomic()
def create_teacher(
    username,
    email,
    first_name,
    last_name,
    school_name,
    password=None,
    output_stream=None,
    styler: Style = None,
):
    def write_output(message: str, style: str = None):
        if output_stream:
            if styler and style:
                message = getattr(styler, style)(message)
            output_stream.write(message)

    user, save_user = User.objects.get_or_create(username=username)
    if save_user:
        if not password:
            password = make_random_password()
        user.first_name = first_name
        user.last_name = last_name
        user.email = email
        user.password = password
    else:
        write_output("Teacher user %s already exists" % username)

    teachers_group = Group.objects.get(name="Teachers")
    if teachers_group.pk not in user.groups.all():
        user.groups.add(teachers_group.pk)
        save_user = True

    if save_user:
        user.save()

    if save_user:
        try:
            teacher = Teacher.objects.get(user=user)
        except ObjectDoesNotExist:
            school, _ = School.objects.get_or_create(name=school_name)
            teacher = Teacher.objects.create(user=user, school=school)
            teacher.save()
            write_output("Teacher %s created" % username)
            return teacher
        else:
            return teacher


def create_teachers_group(
    name: str = "Teachers",
    permissions=(
        "Designate this user as a teacher",
        "Can add project",
        "Can change project",
        "Can delete project",
    ),
    output_stream=None,
    styler: Style = None,
):
    def write_output(message: str, style: str = None):
        if output_stream:
            if styler and style:
                message = getattr(styler, style)(message)
            output_stream.write(message)

    group, created = Group.objects.get_or_create(name=name)
    if created:
        write_output('Successfully created Group "%s"' % group, "SUCCESS")
    else:
        write_output('Group "%s" already exists' % group, "NOTICE")

    for perm in permissions:
        permission = Permission.objects.get(name=perm)
        if permission:
            group.permissions.add(permission)
            write_output(
                '\tAdded Permission "%s" to Group "%s"' % (permission, group), "SUCCESS"
            )
        else:
            write_output("\tNo Permission named %s" % perm, "NOTICE")


class Student(models.Model):
    GENDER_FEMALE = "F"
    GENDER_MALE = "M"
    GENDER_CHOICES = ((GENDER_FEMALE, "Female"), (GENDER_MALE, "Male"))

    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    ethnicity = models.ForeignKey(Ethnicity, on_delete=models.PROTECT)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES)
    teacher = models.ForeignKey(Teacher, on_delete=models.PROTECT)
    grade_level = models.PositiveSmallIntegerField()
    email = models.EmailField(null=True, blank=True)
    project = models.ForeignKey("Project", on_delete=models.SET_NULL, null=True)

    @property
    def full_name(self) -> str:
        """str: Getter for full_name"""
        return self.first_name + " " + self.last_name

    def __str__(self):
        return self.full_name

    class Meta:
        ordering = ("last_name", "first_name")


def create_student(
    first_name,
    last_name,
    ethnicity,
    gender,
    grade_level,
    project,
    teacher,
    email=None,
    output_stream=None,
    styler: Style = None,
):
    def write_output(message: str, style: str = None):
        if output_stream:
            if styler and style:
                message = getattr(styler, style)(message)
            output_stream.write(message)

    student = Student.objects.create(
        first_name=first_name,
        last_name=last_name,
        ethnicity=ethnicity,
        gender=gender,
        grade_level=grade_level,
        project=project,
        teacher=teacher,
    )

    if email:
        student.email = email
        student.save()

    return student


def create_student_from_text(
    first_name,
    last_name,
    eth_name,
    gender,
    teacher_name,
    grade_level,
    project,
    email=None,
    output_stream=None,
):
    def write_output(message):
        if output_stream:
            output_stream.write(message)

    if not first_name:
        write_output("No input data")
        return

    ethnicity, _ = Ethnicity.objects.get_or_create(short_description=eth_name)
    teacher = Teacher.objects.get(user__last_name=teacher_name)

    student, save_student = Student.objects.get_or_create(
        first_name=first_name,
        last_name=last_name,
        defaults={
            "ethnicity": ethnicity,
            "gender": gender,
            "teacher": teacher,
            "grade_level": grade_level,
            "project": project,
        },
    )
    if save_student:
        if email:
            student.email = email
        write_output("Created student %s" % student)
        student.save()
    else:
        write_output("Student already exists: %s" % student)

    return student


class Project(models.Model):
    title = models.CharField(max_length=65)
    abstract = models.TextField(blank=True)
    number = models.CharField(max_length=5, blank=True)
    category = models.ForeignKey(Category, on_delete=models.PROTECT)
    subcategory = models.ForeignKey(Subcategory, on_delete=models.PROTECT)
    division = models.ForeignKey(Division, on_delete=models.PROTECT)
    requires_attention = models.BooleanField(default=False)
    judge_notes = models.TextField(verbose_name="Notes for Judge", blank=True)

    class Meta:
        permissions = (("can_view_results", "Can view project results"),)

    def get_next_number(self):
        def get_max(qs: QuerySet) -> int:
            return qs.aggregate(models.Max("number"))["number__max"]

        max_proj_num = get_max(
            Project.objects.filter(division=self.division, category=self.category)
        )
        if max_proj_num:
            return str(int(max_proj_num) + 1)

        max_proj_num = get_max(Project.objects.all())
        if max_proj_num:
            return str(int(max_proj_num) + 1001 - (int(max_proj_num) % 1000))
        else:
            return str(1001)

    def save(
        self, force_insert=False, force_update=False, using=None, update_fields=None
    ):
        if not self.number:
            self.number = self.get_next_number()
        return super(Project, self).save(
            force_insert, force_update, using, update_fields
        )

    def __str__(self):
        return self.title

    def average_score(self) -> float:
        _sum = 0
        _count = 0
        for ji in self.judginginstance_set.all():
            if ji.has_response():
                _sum += ji.score()
                _count += 1

        if _count == 0:
            return 0
        else:
            return _sum / _count

    def num_scores(self) -> int:
        return len([ji for ji in self.judginginstance_set.all() if ji.has_response()])

    def get_absolute_url(self):
        return reverse("fair_projects:detail", args=(self.number,))

    def student_str(self):
        return ", ".join(str(student) for student in self.student_set.all())

    @classmethod
    def create(
        cls, title, abstract, category, subcategory, division, output_stream=None
    ) -> "Project":
        """Create a project."""

        def write_output(message):
            if output_stream:
                output_stream.write(message)

        project = cls.objects.create(
            title=title,
            abstract=abstract,
            category=category,
            subcategory=subcategory,
            division=division,
        )

        write_output("Created project: %s" % project)

        return project


class JudgingInstance(models.Model):
    judge = models.ForeignKey(Judge, models.CASCADE)
    project = models.ForeignKey(Project, models.CASCADE)
    response = models.ForeignKey(
        "rubrics.RubricResponse", models.CASCADE, null=True, blank=True
    )
    locked = models.BooleanField(default=False)

    def __init__(self, *args, **kwargs):
        rubric = kwargs.pop("rubric", None)
        super(JudgingInstance, self).__init__(*args, **kwargs)
        if not self.response and rubric:
            self.response = RubricResponse.objects.create(rubric=rubric)

    def __str__(self):
        return "{0} - {1}: {2}".format(
            self.judge, self.project, self.response.rubric.name
        )

    def score(self):
        return self.response.score()

    def has_response(self):
        return self.response.has_response

    def complete(self):
        return self.response.complete

    def set_locked(self):
        if not self.locked:
            self.locked = True
            self.save()

    class JudgingInstanceManager(models.Manager):
        def get_queryset(self) -> QuerySet["JudgingInstance"]:
            return super().get_queryset().select_related("judge", "project", "response")

        def for_project(self, project: Project | int) -> QuerySet["JudgingInstance"]:
            if isinstance(project, Project):
                kwargs = {"project": project}
            else:
                kwargs = {"project_id": project}

            return self.get_queryset().filter(**kwargs)

        def to_rubric_responses(
            self, judging_instances: QuerySet["JudgingInstance"]
        ) -> QuerySet[RubricResponse]:
            """
            Args:
                judging_instances (QuerySet[JudgingInstance]):


            Returns:
                QuerySet[RubricResponse]: a queryset of RubricResponses for the
                    given queryset of JudgingInstances
            """
            response_ids = judging_instances.values_list("response__id", flat=True)
            return RubricResponse.objects.filter(id__in=response_ids)

    objects = JudgingInstanceManager()

    class LockedInstanceManager(JudgingInstanceManager):
        def get_queryset(self) -> QuerySet["JudgingInstance"]:
            return super().get_queryset().filter(locked=True)

    locked_objects = LockedInstanceManager()

    class UnlockedInstanceManager(JudgingInstanceManager):
        def get_queryset(self) -> QuerySet["JudgingInstance"]:
            return super().get_queryset().filter(locked=False)

    unlocked_objects = UnlockedInstanceManager()
