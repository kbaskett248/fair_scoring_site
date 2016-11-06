from collections import OrderedDict

from django.contrib.auth.models import User, Group
from django.core.exceptions import ObjectDoesNotExist
from django.core.management import call_command
from django.test import TestCase
from django.utils.six import StringIO
from model_mommy import mommy

from fair_categories.models import Category, Division, Subcategory
from fair_projects.models import School, create_teacher, Teacher, create_teachers_group, Student, Project, \
    JudgingInstance
from judges.models import Judge
from rubrics.models import Question, Choice, Rubric
from rubrics.models import RubricResponse


def make_school(name: str='Test School') -> School:
    return mommy.make(School, name=name)


class SchoolTests(TestCase):
    def test_create_school(self):
        school = make_school('Test School')
        self.assertIsNotNone(school)
        self.assertIsInstance(school, School)
        self.assertQuerysetEqual(School.objects.all(),
                                 ['<School: Test School>'])

    def test_str(self, school_name: str='Test School'):
        school = make_school(school_name)
        self.assertEqual(str(school), school_name)


class TeacherTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        create_teachers_group()

    def setUp(self):
        self.teachers_group = Group.objects.get(name='Teachers')

    def assert_teacher_is_correct(self, teacher: Teacher,
                                  teacher_repr='<Teacher: Teddy Testerson>',
                                  user_repr='<User: test_teacher>',
                                  school_repr='<School: Test School>'):
        # Teacher is correct
        self.assertIsNotNone(teacher)
        self.assertIsInstance(teacher, Teacher)
        self.assertQuerysetEqual(Teacher.objects.all(),
                                 [teacher_repr])

        # User is correct
        self.assertIsInstance(teacher.user, User)
        self.assertQuerysetEqual(User.objects.all(),
                                 [user_repr])
        self.assertIn(self.teachers_group, teacher.user.groups.all())
        self.assertTrue(teacher.user.has_perm('fair_projects.is_teacher'))

        # School is correct
        self.assertIsInstance(teacher.school, School)
        self.assertQuerysetEqual(School.objects.all(),
                                 [school_repr])

    def create_and_test_teacher(self, data_dict: OrderedDict):
        teacher = create_teacher(*list(data_dict.values()))
        self.assert_teacher_is_correct(
            teacher,
            teacher_repr='<Teacher: {first_name} {last_name}>'.format(**data_dict),
            user_repr='<User: {username}>'.format(**data_dict),
            school_repr='<School: {school}>'.format(**data_dict))

    def test_create_teacher_with_no_user_or_school(self):
        data_dict = OrderedDict()
        data_dict['username'] = 'test_teacher'
        data_dict['email'] = 'test@test.com'
        data_dict['first_name'] = 'Teddy'
        data_dict['last_name'] = 'Testerson'
        data_dict['school'] = 'Test School'

        self.create_and_test_teacher(data_dict)

    def test_create_teacher_with_existing_user(self):
        data_dict = OrderedDict()
        data_dict['username'] = 'test_teacher_2'
        data_dict['email'] = 'test2@test.com'
        data_dict['first_name'] = 'Terrence'
        data_dict['last_name'] = 'Testerson'
        data_dict['school'] = 'Test School 2'

        user = User.objects.create_user(data_dict['username'],
                                        email=data_dict['email'],
                                        first_name=data_dict['first_name'],
                                        last_name=data_dict['last_name'])
        # Establish initial state
        self.assertQuerysetEqual(User.objects.all(),
                                 ['<User: {username}>'.format(**data_dict)])

        self.create_and_test_teacher(data_dict)

    def test_create_teacher_with_existing_school(self):
        data_dict = OrderedDict()
        data_dict['username'] = 'test_teacher_3'
        data_dict['email'] = 'test3@test.com'
        data_dict['first_name'] = 'Tiffany'
        data_dict['last_name'] = 'Testerson'
        data_dict['school'] = 'Test School 3'

        School.objects.create(name=data_dict['school'])
        # Establish initial state
        self.assertQuerysetEqual(School.objects.all(),
                                 ['<School: {school}>'.format(**data_dict)])

        self.create_and_test_teacher(data_dict)


class InitGroupsTest(TestCase):
    def test_init_groups(self):
        out = StringIO()
        call_command('initgroups', stdout=out)

        fair_runners_group = Group.objects.get(name='Fair runners')
        self.assertIsNotNone(fair_runners_group)
        self.assertQuerysetEqual(fair_runners_group.permissions.all(),
                                 ['<Permission: auth | group | Can add group>',
                                  '<Permission: auth | user | Can add user>',
                                  '<Permission: auth | user | Can change user>',
                                  '<Permission: auth | user | Can delete user>',
                                  '<Permission: judges | judge | Can add judge>',
                                  '<Permission: judges | judge | Can change judge>',
                                  '<Permission: judges | judge | Can delete judge>']
                                 )

        judges_group = Group.objects.get(name='Judges')
        self.assertIsNotNone(judges_group)
        self.assertQuerysetEqual(judges_group.permissions.all(),
                                 ['<Permission: judges | judge | Designates this user as a judge>'])

        teachers_group = Group.objects.get(name='Teachers')
        self.assertIsNotNone(teachers_group)
        self.assertQuerysetEqual(teachers_group.permissions.all(),
                                 ['<Permission: fair_projects | project | Can add project>',
                                  '<Permission: fair_projects | project | Can change project>',
                                  '<Permission: fair_projects | project | Can delete project>',
                                  '<Permission: fair_projects | teacher | Designate this user as a teacher>']
                                 )


def make_student(**kwargs) -> Student:
    return mommy.make(Student, **kwargs)


class StudentTests(TestCase):
    def test_str(self, first_name: str='Diana', last_name: str='Prince'):
        student = make_student(first_name=first_name, last_name=last_name)
        self.assertEqual(str(student), '{0} {1}'.format(first_name, last_name))


def make_project(category_name: str=None, division_name: str=None, **kwargs):
    if category_name:
        try:
            kwargs['subcategory'] = Subcategory.objects.select_related('category')\
                .get(category__short_description=category_name)
            kwargs['category'] = kwargs['subcategory'].category
        except ObjectDoesNotExist:
            kwargs['category'] = mommy.make(Category, short_description=category_name)
            kwargs['subcategory'] = mommy.make(Subcategory, short_description='Subcategory of %s' % category_name,
                                               category=kwargs['category'])
    if division_name:
        try:
            kwargs['division'] = Division.objects.get(short_description=division_name)
        except ObjectDoesNotExist:
            kwargs['division'] = mommy.make(Division, short_description=division_name)
    return mommy.make(Project, number=None, **kwargs)


class ProjectTests(TestCase):
    def setUp(self):
        self.rubric = make_rubric()
        user = mommy.make(User, first_name='Dallas', last_name='Green')
        self.judge = make_judge(user=user)

    def test_str(self, project_title: str='The effect of her presence on the amount of sunshine') -> None:
        project = make_project(title=project_title)
        self.assertEqual(str(project), project_title)

    def test_get_next_number(self):
        data = (
            ('PH', 1001),
            ('PH', 1002),
            ('LM', 2001),
            ('LH', 3001),
            ('PM', 4001),
            ('PH', 1003),
            ('LH', 3002),
            ('LM', 2002)
        )
        cats = {'P': 'Physical Sciences', 'L': 'Life Sciences'}
        divs = {'H': 'High School', 'M': 'Middle School'}
        def get_new_project(code):
            kwargs = {}
            kwargs['category_name'] = cats[code[0]]
            kwargs['division_name'] = divs[code[1]]
            return make_project(**kwargs)

        for code, number in data:
            project = get_new_project(code)
            self.assertEqual(project.number, number)

    def test_average_score_is_zero_for_project_with_no_instances(self):
        project = make_project()
        self.assertEqual(project.average_score(), 0,
                         msg='average_score should be zero for project with no judging instances')

    def test_average_score_is_zero_for_project_with_unanswered_responses(self):
        project = make_project()
        make_judging_instance(project)
        self.assertEqual(project.average_score(), 0,
                         msg='average_score should be zero for project with unanswered judging instances')

    def test_average_score_is_equal_to_instance_score(self):
        project = make_project()
        ji = make_judging_instance(project)
        answer_rubric_response(ji.response)
        self.assertGreater(project.average_score(), 0,
                           msg='average_score should be greater than zero for project with answered judging instances')
        self.assertEqual(project.average_score(), ji.score(),
                         msg='average_score should be equal to JudgingInstance score when there is only one judging instance')



def make_rubric():
    rubric = mommy.make(Rubric, name="Test Rubric")
    default_weight = float('{0:.3f}'.format(1 / len(Question.CHOICE_TYPES)))
    for question_type in Question.available_types():
        question_is_choice_type = question_type in Question.CHOICE_TYPES
        weight = 0
        if question_is_choice_type:
            weight = default_weight
        question = mommy.make(Question,
                              rubric=rubric,
                              short_description='Question %s' % question_type,
                              long_description='This is for question %s' % question_type,
                              help_text='This is help text for question %s' % question_type,
                              weight=weight,
                              question_type=question_type,
                              required=True)
        if question_is_choice_type:
            for key in range(1, 4):
                mommy.make(Choice, question=question, order=key,
                           key=str(key), description='Choice %s' % key)
    return rubric


def make_rubric_response(rubric=None):
    if not rubric:
        rubric = make_rubric()

    return mommy.make(RubricResponse, rubric=rubric)


def answer_rubric_response(rubric_response):
    for q_resp in rubric_response.questionresponse_set.all():
        if q_resp.question.question_type == Question.MULTI_SELECT_TYPE:
            q_resp.update_response(['1', '2'])
        elif q_resp.question.question_type == Question.LONG_TEXT:
            q_resp.update_response('This is a long text response.\nThis is a second line')
        else:
            q_resp.update_response('1')


def make_judge(phone: str='867-5309', **kwargs):
    return mommy.make(Judge, phone=phone, **kwargs)


def make_judging_instance(project: Project, judge: Judge=None, rubric: Rubric=None):
    if not judge:
        judge = make_judge()

    if not rubric:
        rubric = make_rubric()

    return JudgingInstance.objects.create(project=project,
                                          judge=judge,
                                          rubric=rubric)


class JudgingInstanceTests(TestCase):
    def setUp(self):
        self.rubric = make_rubric()
        self.school = make_school()
        user = mommy.make(User, first_name='Dallas', last_name='Green')
        self.judge = make_judge(user=user)
        self.project = make_project(title='Test Project')

    def test_create_judging_instance_with_rubric(self):
        ji = make_judging_instance(self.project, judge=self.judge, rubric=self.rubric)
        self.assertIsInstance(ji, JudgingInstance)
        self.assertIsNotNone(ji.response)
        self.assertIsInstance(ji.response, RubricResponse)

    def test_judging_instance_string_method(self):
        ji = make_judging_instance(self.project, judge=self.judge, rubric=self.rubric)
        self.assertIn(str(self.judge), str(ji))
        self.assertIn(str(self.project), str(ji))
        self.assertIn(str(self.rubric.name), str(ji))

    def test_score_is_zero_for_unanswered_rubric(self):
        ji = make_judging_instance(self.project, judge=self.judge, rubric=self.rubric)
        self.assertEqual(ji.score(), 0,
                         msg='Score is not zero for unanswered rubrics')
        self.assertFalse(ji.has_response(),
                         msg='has_response should be False for unanswered rubrics')

    def test_score_is_non_zero_for_answered_rubrics(self):
        ji = make_judging_instance(self.project, judge=self.judge, rubric=self.rubric)
        answer_rubric_response(ji.response)
        self.assertTrue(ji.has_response(),
                        msg='has_response should be True for answered rubrics')
        self.assertNotEqual(ji.score(), 0,
                            msg='Score should be non-zero for answered rubrics')
        self.assertGreater(ji.score(), 0,
                           msg='Score should be non-zero for answered rubrics')
