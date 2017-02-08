from collections import OrderedDict

from django.contrib.auth.models import User, Group, Permission
from django.core.exceptions import ObjectDoesNotExist
from django.core.management import call_command
from django.test import Client
from django.test import TestCase
from django.urls import reverse
from django.utils.six import StringIO
from model_mommy import mommy

from fair_categories.models import Category, Division, Subcategory
from fair_projects.admin import ProjectResource
from fair_projects.logic import assign_judges, get_projects_sorted_by_score, get_question_feedback_dict
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
    def test_str(self, project_title: str='The effect of her presence on the amount of sunshine') -> None:
        project = make_project(title=project_title)
        self.assertEqual(str(project), project_title)

    def test_get_next_number(self):
        data = (
            ('PH', '1001'),
            ('PH', '1002'),
            ('LM', '2001'),
            ('LH', '3001'),
            ('PM', '4001'),
            ('PH', '1003'),
            ('LH', '3002'),
            ('LM', '2002')
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

    def test_num_scores_is_zero_for_project_with_no_rubrics(self):
        project = make_project()
        self.assertEqual(project.num_scores(), 0,
                         msg='Project with no scores has non-zero num_scores')

    def test_num_scores_is_equal_to_the_number_of_answered_rubrics(self):
        project = make_project()
        judging_instances = [make_judging_instance(project) for _ in range(1, 10)]
        self.assertEqual(project.num_scores(), 0,
                         msg='Project with no scores has non-zero num_scores')

        for count, ji in enumerate(judging_instances, start=1):
            answer_rubric_response(ji.response)
            self.assertEqual(project.num_scores(), count)


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
    @classmethod
    def setUpTestData(cls):
        cls.rubric = make_rubric()
        cls.school = make_school()
        user = mommy.make(User, first_name='Dallas', last_name='Green')
        cls.judge = make_judge(user=user)
        cls.project = make_project(title='Test Project')

    def setUp(self):
        self.ji = make_judging_instance(self.project, judge=self.judge, rubric=self.rubric)

    def test_create_judging_instance_with_rubric(self):
        self.assertIsInstance(self.ji, JudgingInstance)
        self.assertIsNotNone(self.ji.response)
        self.assertIsInstance(self.ji.response, RubricResponse)

    def test_judging_instance_string_method(self):
        self.assertIn(str(self.judge), str(self.ji))
        self.assertIn(str(self.project), str(self.ji))
        self.assertIn(str(self.rubric.name), str(self.ji))

    def test_score_is_zero_for_unanswered_rubric(self):
        self.assertEqual(self.ji.score(), 0,
                         msg='Score is not zero for unanswered rubrics')
        self.assertFalse(self.ji.has_response(),
                         msg='has_response should be False for unanswered rubrics')

    def test_score_is_non_zero_for_answered_rubrics(self):
        answer_rubric_response(self.ji.response)
        self.assertTrue(self.ji.has_response(),
                        msg='has_response should be True for answered rubrics')
        self.assertNotEqual(self.ji.score(), 0,
                            msg='Score should be non-zero for answered rubrics')
        self.assertGreater(self.ji.score(), 0,
                           msg='Score should be non-zero for answered rubrics')


class TestJudgeAssignmentAndProjectScoring(TestCase):
    fixtures = ['divisions_categories.json',
                'ethnicities.json',
                'schools.json',
                'teachers.json',
                'projects_small.json',
                'judges.json',
                'rubric.json']

    @classmethod
    def setUpTestData(cls):
        assign_judges()

    def test_judge_assignment_creates_judging_instances(self):
        self.assertGreater(JudgingInstance.objects.all().count(), 0,
                           msg='Judge assignment produced no judging instances.')

    def test_judge_assignment_is_steady(self):
        qs = JudgingInstance.objects.order_by('pk')
        existing_instances = map(repr, qs.all())
        assign_judges()
        self.assertQuerysetEqual(qs.all(), existing_instances,
                                 msg='Judge assignment is not steady. Assigning again without changed inputs results in changed assignments.')

    def test_unanswered_projects_are_sorted_by_project_number(self):
        project_list = get_projects_sorted_by_score()
        for project1, project2 in zip(project_list[:-1], project_list[1:]):
            self.assertLess(project1.number, project2.number,
                            msg='Unanswered Projects are not sorted by project number')

    def test_answered_projects_come_first(self):
        project1 = Project.objects.last()
        ji = project1.judginginstance_set.first()
        answer_rubric_response(ji.response)

        project_list = get_projects_sorted_by_score()
        self.assertEqual(project_list[0], project1,
                         msg='First project in list is not the project that was scored')

        project2 = project_list[-1]
        ji = project2.judginginstance_set.first()
        answer_rubric_response(ji.response)

        project_list = get_projects_sorted_by_score()
        if project_list[0].average_score() == project_list[1].average_score():
            self.assertLessEqual(project_list[0].number, project_list[1].number,
                                 msg='Projects with equal scores are not sorted by number')
        else:
            self.assertGreater(project_list[0].average_score(), project_list[1].average_score(),
                               msg='Score of 2nd project is greater than score of 1st project')

    def test_projects_with_more_answers_come_first(self):
        self.test_answered_projects_come_first()

        project_list = get_projects_sorted_by_score()
        self.assertEqual(project_list[0].average_score(), project_list[1].average_score(),
                         msg='This test requires 2 projects with equal scores')

        def get_unanswered_response(project: Project) -> RubricResponse:
            for ji in project.judginginstance_set.all():
                if not ji.has_response():
                    return ji.response

        project = project_list[1]
        answer_rubric_response(get_unanswered_response(project))

        project_list = get_projects_sorted_by_score()
        self.assertEqual(project_list[0], project,
                         msg='If scores are equal, projects with more responses should come first')


class TestResultsPage(TestCase):
    fixtures = ['divisions_categories.json',
                'ethnicities.json',
                'schools.json',
                'teachers.json',
                'projects_small.json',
                'judges.json',
                'rubric.json']

    @classmethod
    def setUpTestData(cls):
        assign_judges()
        cls.client = Client()
        cls.user_without_permission = User.objects.create_user(
            'user_without_permission', password='user_without_permission')
        cls.user_with_permission = User.objects.create_user(
            'user_with_permission', password='user_with_permission')

        permission = Permission.objects.get(codename='can_view_results')
        cls.user_with_permission.user_permissions.add(permission)

        cls.results_url = reverse('fair_projects:project_results')
        cls.results_link = '<a href="%s">Results</a>' % cls.results_url

    def test_results_view_redirects_anonymous(self):
        response = self.client.get(self.results_url, follow=True)
        self.assertRedirects(response, reverse('login') + '?next=/projects/results',
                             msg_prefix='View did not redirect anonymous user')
        
    def test_results_view_redirects_user_without_permission(self):
        self.client.login(username='user_without_permission', password='user_without_permission')
        response = self.client.get(self.results_url, follow=True)
        self.assertRedirects(response, reverse('login') + '?next=/projects/results',
                             msg_prefix='View did not redirect user without permission')

    def test_results_view_permits_user_with_permission(self):
        self.client.login(username='user_with_permission', password='user_with_permission')
        response = self.client.get(self.results_url, follow=True)
        self.assertEqual(response.status_code, 200,
                         msg='Results page returned invalid status code')
        self.assertIsNotNone(response.context['project_list'],
                             msg='Results page does not contain project list')
        self.assertTemplateUsed(response, 'fair_projects/results.html',
                                msg_prefix='Results page did not use the appropriate template')

    def test_no_link_to_results_for_anonymous(self):
        response = self.client.get(reverse('fair_projects:index'), follow=True)
        self.assertNotContains(response, self.results_link, html=True,
                               msg_prefix='Results link appears for anonymous users')

    def test_no_link_to_results_for_user_without_permission(self):
        self.client.login(username='user_without_permission', password='user_without_permission')
        response = self.client.get(reverse('fair_projects:index'), follow=True)
        self.assertNotContains(response, self.results_link, html=True,
                               msg_prefix='Results link appears for anonymous users')

    def test_link_to_results_present_for_user_with_permissions(self):
        self.client.login(username='user_with_permission', password='user_with_permission')
        response = self.client.get(reverse('fair_projects:index'), follow=True)
        self.assertContains(response, self.results_link, html=True,
                            msg_prefix='Results link does not appear for user with correct permissions')


class TestQuestionFeedbackDict(TestCase):
    fixtures = ['divisions_categories.json',
                'ethnicities.json',
                'schools.json',
                'teachers.json',
                'projects_small.json',
                'judges.json',
                'rubric.json']

    def setUp(self):
        assign_judges()

    def test_question_feedback_dict_includes_all_questions(self):
        project = Project.objects.last()
        ji = project.judginginstance_set.first()
        answer_rubric_response(ji.response)
        question_feedback_dict = get_question_feedback_dict(project)
        for question in ji.response.rubric.question_set.all():
            self.assertIsNotNone(question_feedback_dict[question.short_description])


class TestProjectResource(TestCase):
    @classmethod
    def setUpClass(cls):
        super(TestProjectResource, cls).setUpClass()

        cls.labels = ('number', 'title', 'category', 'subcategory', 'division')

        cls.resource = ProjectResource()
        cls.category = mommy.make(Category, short_description='Category 1')
        cls.subcategory = mommy.make(Subcategory, short_description='Subcategory 1',
                                     category=cls.category)
        cls.division = mommy.make(Division, short_description='Division 1')
        cls.instance = mommy.make(Project,
                                  category=cls.category,
                                  subcategory=cls.subcategory,
                                  division=cls.division)

    def test_export_headers(self):
        dataset = self.resource.export()
        for index, label in enumerate(self.labels):
            self.assertEqual(dataset.headers[index], label)

    def test_export_data(self):
        dataset = self.resource.export()
        for key in self.labels:
            self.assertEqual(dataset.dict[0][key], str(getattr(self.instance, key, None)))

