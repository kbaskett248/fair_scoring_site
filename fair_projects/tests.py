from collections import OrderedDict

from django.contrib.auth.models import User, Group
from django.core.management import call_command
from django.test import TestCase
from django.utils.six import StringIO

from fair_projects.models import School, create_teacher, Teacher, create_teachers_group


class SchoolTests(TestCase):
    def test_create_school(self):
        school = School.objects.create(name='Test School')
        self.assertIsNotNone(school)
        self.assertIsInstance(school, School)
        self.assertQuerysetEqual(School.objects.all(),
                                 ['<School: Test School>'])


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
