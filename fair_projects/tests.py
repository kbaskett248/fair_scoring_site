from collections import OrderedDict

from django.contrib.auth.models import User, Group
from django.core.exceptions import ObjectDoesNotExist
from django.core.management import call_command
from django.test import TestCase
from django.utils.six import StringIO
from model_mommy import mommy

from fair_categories.models import Category, Division, Subcategory
from fair_projects.models import School, create_teacher, Teacher, create_teachers_group, Student, Project


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
