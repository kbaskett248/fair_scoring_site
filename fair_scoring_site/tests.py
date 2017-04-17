import itertools

from collections import defaultdict
from django.contrib.auth.models import User
from django.core.management import call_command
from django.db.models import Count
from hypothesis.extra.django import TestCase as HypTestCase
from model_mommy import mommy

from awards.models import Is, In
from fair_categories.models import Category, Subcategory, Division
from fair_projects.models import Project, JudgingInstance
from fair_scoring_site.admin import AwardRuleForm
from fair_scoring_site.logic import get_judging_rubric_name, get_judging_rubric, get_num_judges_per_project, \
    get_num_projects_per_judge
from judges.models import Judge
import rubrics.fixtures


project_number_counter = 1000


def make_test_category(short_description: str) -> Category:
    return Category.objects.create(short_description=short_description)


def make_test_subcategory(category: Category, short_description: str) -> Subcategory:
    return mommy.make(Subcategory,
                      short_description=short_description,
                      category=category)


def make_test_division(short_description: str) -> Division:
    return Division.objects.create(short_description=short_description)


def make_test_judge(categories: [Category], divisions: [Division], active=True) -> Judge:
    user = mommy.make(User, is_active=active, first_name='Test', last_name='Judge')
    judge = mommy.make(Judge, phone="770-867-5309", user=user)
    judge.categories = categories
    judge.divisions = divisions
    judge.save()
    return judge


def make_test_project(subcategory: Subcategory, division: Division) -> Project:
    global project_number_counter
    project_number_counter += 1
    return mommy.make(Project,
                      number=project_number_counter,
                      subcategory=subcategory,
                      category=subcategory.category,
                      division=division)


def make_test_rubric():
    return rubrics.fixtures.make_test_rubric(get_judging_rubric_name())


class AwardRuleFormTests(HypTestCase):
    @classmethod
    def setUpClass(cls):
        super(AwardRuleFormTests, cls).setUpClass()
        Category.objects.create(short_description='Category 1')
        Category.objects.create(short_description='Category 2')

        mommy.make(Subcategory, short_description='Subcategory 1')
        mommy.make(Subcategory, short_description='Subcategory 2')

        Division.objects.create(short_description='Division 1')
        Division.objects.create(short_description='Division 2')

        mommy.make(Project, number=1001)
        mommy.make(Project, number=1002)

    def success_test(self, trait: str, operator: str, value: str):
        data = {'trait': trait,
                'operator_name': operator,
                'value': value}
        form = AwardRuleForm(data)
        self.assertTrue(form.is_valid())

    def failed_test(self, trait: str, operator: str, value: str):
        data = {'trait': trait,
                'operator_name': operator,
                'value': value}
        form = AwardRuleForm(data)
        self.assertFalse(form.is_valid())

    def trait_validation_test(self, trait: str, good_values: list, bad_value: str):
        with self.subTest('Validation succeeds for single {trait} when value exists'.format(
                trait=trait)):
            self.success_test(trait, Is.internal, good_values[0])

        with self.subTest('Validation fails for single {trait} when value does not exist'.format(
                trait=trait)):
            self.failed_test(trait, Is.internal, bad_value)

        with self.subTest('Validation succeeds for {trait} IN when single value exists'.format(
                trait=trait)):
            self.success_test(trait, In.internal, good_values[0])

        with self.subTest('Validation fails for {trait} IN when single value does not exist'.format(
                trait=trait)):
            self.failed_test(trait, In.internal, bad_value)

        with self.subTest('Validation succeeds for {trait} IN when all values exist'.format(
                trait=trait)):
            self.success_test(trait, In.internal, ', '.join(good_values))

        with self.subTest('Validation fails for {trait} IN when any value does not exist'.format(
                trait=trait)):
            self.failed_test(trait, In.internal, ', '.join(good_values + [bad_value]))

    def test_category_validation(self):
        self.trait_validation_test('category', ['Category 1', 'Category 2'], 'Category 0')

    def test_subcategory_validation(self):
        self.trait_validation_test('subcategory', ['Subcategory 1', 'Subcategory 2'], 'Subcategory 0')

    def test_division_validation(self):
        self.trait_validation_test('division', ['Division 1', 'Division 2'], 'Division 0')

    def test_number_validation(self):
        self.trait_validation_test('number', ['1001', '1002'], '2001')

    def test_grade_validation(self):
        self.trait_validation_test('grade_level', ['1', '6', '11', '12'], '13')


class AssignmentTests(HypTestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super(AssignmentTests, cls).setUpClass()
        make_test_rubric()

        cls.category1 = make_test_category('Category 1')
        cls.category2 = make_test_category('Category 2')

        cls.subcategory1 = make_test_subcategory(cls.category1, 'Subcategory 1')
        cls.subcategory2 = make_test_subcategory(cls.category2, 'Subcategory 2')

        cls.division1 = make_test_division('Division 1')
        cls.division2 = make_test_division('Division 2')

    @staticmethod
    def _instance_exists(project: Project, judge: Judge) -> bool:
        return JudgingInstance.objects.filter(project=project, judge=judge).exists()

    @staticmethod
    def _instance_count(project: Project, judge: Judge) -> int:
        return JudgingInstance.objects.filter(project=project, judge=judge).count()

    def assertOnlyOneJudgingInstance(self, project: Project, judge: Judge, msg: str=None) -> None:
        if not msg:
            msg = 'There is not 1 JudgingInstnace for Project ({}) and judge ({})'.format(
                project, judge
            )
        self.assertEqual(self._instance_count(project, judge), 1, msg)

    def assertProjectAssignedToJudge(self, project: Project, judge: Judge, msg: str=None) -> None:
        if not msg:
            msg = 'Project ({}) not assigned to judge ({})'.format(
                project, judge
            )
        self.assertTrue(self._instance_exists(project, judge), msg)

    def assertProjectNotAssignedToJudge(self, project: Project, judge: Judge, msg: str=None) -> None:
        if not msg:
            msg = 'Project ({}) assigned to judge ({})'.format(
                project, judge
            )
        self.assertFalse(self._instance_exists(project, judge), msg)


class JudgeAssignmentTests(AssignmentTests):
    @classmethod
    def setUpClass(cls) -> None:
        super(JudgeAssignmentTests, cls).setUpClass()
        cls.judge = make_test_judge(categories=[cls.category1], divisions=[cls.division1])
        cls.inactive_judge = make_test_judge(categories=[cls.category2],
                                             divisions=[cls.division2],
                                             active=False)
        cls.multiple_judge = make_test_judge(categories=[cls.category1, cls.category2],
                                             divisions=[cls.division1, cls.division2])

    # An existing judge is assigned to a new project if the category and division match
    def test_judge_assigned_for_matching_category_and_division(self):
        project = make_test_project(self.subcategory1, self.division1)
        self.assertProjectAssignedToJudge(project, self.judge)
        self.assertOnlyOneJudgingInstance(project, self.judge)

    # An existing judge is only assigned to a new project once
    def test_judge_assigned_once(self):
        project = make_test_project(self.subcategory1, self.division1)
        self.assertProjectAssignedToJudge(project, self.judge)
        self.assertOnlyOneJudgingInstance(project, self.judge)

        project.save()
        self.assertOnlyOneJudgingInstance(project, self.judge)

    # An existing judge is not assigned to a new project if the category and division do not match
    def test_judge_not_assigned_for_mismatched_category(self):
        project = make_test_project(self.subcategory2, self.division1)
        self.assertProjectNotAssignedToJudge(project, self.judge)

    def test_judge_not_assigned_for_mismatched_division(self):
        project = make_test_project(self.subcategory1, self.division2)
        self.assertProjectNotAssignedToJudge(project, self.judge)

    # An existing inactive judge is not assigned to a new project
    def test_inactive_judge_not_assigned(self):
        project = make_test_project(self.subcategory2, self.division2)
        self.assertProjectNotAssignedToJudge(project, self.inactive_judge)

    def test_judge_with_multiple_categories_and_divisions_assigned_to_new_project(self):
        project = make_test_project(self.subcategory2, self.division2)
        self.assertProjectAssignedToJudge(project, self.multiple_judge)
        self.assertOnlyOneJudgingInstance(project, self.multiple_judge)

    def test_judge_removed_if_category_no_longer_matches(self):
        project = make_test_project(self.subcategory1, self.division1)
        self.assertProjectAssignedToJudge(project, self.judge)

        project.category = self.category2
        project.subcategory = self.subcategory2
        project.save()
        self.assertProjectNotAssignedToJudge(project, self.judge)

    def test_judge_removed_if_division_no_longer_matches(self):
        project = make_test_project(self.subcategory1, self.division1)
        self.assertProjectAssignedToJudge(project, self.judge)

        project.division = self.division2
        project.save()
        self.assertProjectNotAssignedToJudge(project, self.judge)


class ProjectAssignmentTests(AssignmentTests):
    @classmethod
    def setUpClass(cls) -> None:
        super(ProjectAssignmentTests, cls).setUpClass()
        cls.project = make_test_project(cls.subcategory1, cls.division1)

    # An existing project is assigned to a new judge if the category and division match
    def test_project_assigned_for_matching_category_and_division(self):
        judge = make_test_judge(categories=[self.category1], divisions=[self.division1])
        self.assertProjectAssignedToJudge(self.project, judge)
        self.assertOnlyOneJudgingInstance(self.project, judge)

    # An existing project is only assigned to a new judge once
    def test_project_assigned_once(self):
        judge = make_test_judge(categories=[self.category1], divisions=[self.division1])
        self.assertProjectAssignedToJudge(self.project, judge)
        self.assertOnlyOneJudgingInstance(self.project, judge)

        judge.save()
        self.assertOnlyOneJudgingInstance(self.project, judge)

    # An existing project is not assigned to a new judge if the category and division do not match
    def test_project_not_assigned_for_mismatched_category(self):
        judge = make_test_judge(categories=[self.category2], divisions=[self.division1])
        self.assertProjectNotAssignedToJudge(self.project, judge)

    def test_project_not_assigned_for_mismatched_division(self):
        judge = make_test_judge(categories=[self.category1], divisions=[self.division2])
        self.assertProjectNotAssignedToJudge(self.project, judge)

    # An existing project is not assigned to a new inactive judge
    def test_project_not_assigned_to_inactive_judge(self):
        judge = make_test_judge(categories=[self.category1],
                                divisions=[self.division1],
                                active=False)
        self.assertProjectNotAssignedToJudge(self.project, judge)

    def test_project_assigned_to_judge_with_multiple_categories_and_divisions(self):
        judge = make_test_judge(categories=[self.category1, self.category2],
                                divisions=[self.division1, self.division2])
        self.assertProjectAssignedToJudge(self.project, judge)
        self.assertOnlyOneJudgingInstance(self.project, judge)

    def test_project_removed_if_category_no_longer_matches(self):
        judge = make_test_judge(categories=[self.category1], divisions=[self.division1])
        self.assertProjectAssignedToJudge(self.project, judge)

        judge.categories = [self.category2]
        judge.save()
        self.assertProjectNotAssignedToJudge(self.project, judge)

    def test_project_removed_if_division_no_longer_matches(self):
        judge = make_test_judge(categories=[self.category1], divisions=[self.division1])
        self.assertProjectAssignedToJudge(self.project, judge)

        judge.divisions = [self.division2]
        judge.save()
        self.assertProjectNotAssignedToJudge(self.project, judge)

    def test_project_removed_if_judge_changed_to_inactive(self):
        judge = make_test_judge(categories=[self.category1], divisions=[self.division1])
        self.assertProjectAssignedToJudge(self.project, judge)

        judge.user.is_active = False
        judge.user.save()
        self.assertProjectNotAssignedToJudge(self.project, judge)


class BulkAssignmentTests(HypTestCase):
    fixtures = ['divisions_categories.json',
                'ethnicities.json',
                'schools.json',
                'teachers.json',
                'rubric.json']

    @classmethod
    def setUpClass(cls):
        super(BulkAssignmentTests, cls).setUpClass()
        cls.rubric = get_judging_rubric()
        cls.min_num_judges = get_num_judges_per_project()
        cls.min_num_projects = get_num_projects_per_judge()
        cls.groups = cls.get_groups()

    @staticmethod
    def get_groups():
        categories = list(Category.objects.all())
        divisions = list(Category.objects.all())
        return list(itertools.product(categories, divisions))

    @staticmethod
    def load_fixture(fixture_name: str) -> None:
        call_command('loaddata', fixture_name)

    def get_judges(self):
        queryset = Judge.objects.filter(user__is_active=True)\
                                .annotate(num_projects=Count('judginginstance'))\
                                .prefetch_related('categories', 'divisions')
        return list(queryset.all())

    def get_projects(self):
        queryset = Project.objects.annotate(num_judges=Count('judginginstance'))
        return list(queryset.all())

    def assertWithinBounds(self):
        judge_minimums = self.get_minimum_num_judges_by_group()
        for project in self.get_projects():
            print(project, project.category, project.division, project.num_judges)
            self.assertGreaterEqual(project.num_judges,
                                    judge_minimums[(project.category_id, project.division_id)])

        project_minimums = self.get_minimum_num_projects_by_group()
        for judge in self.get_judges():
            judge_min = 0

            for cat, div in self.judge_group_iterator(judge):
                judge_min = max(judge_min, project_minimums[(cat, div)])

            print(judge, judge.num_projects)
            self.assertGreaterEqual(judge.num_projects,
                                    judge_min)

    @staticmethod
    def judge_group_iterator(judge: Judge):
        cats = [cat.pk for cat in judge.categories.all()]
        divs = [div.pk for div in judge.divisions.all()]
        return itertools.product(cats, divs)

    @staticmethod
    def get_project_counts_by_group() -> dict:
        project_counts = defaultdict(lambda: 0)
        for project in Project.objects.all():
            cat = project.category_id
            div = project.division_id
            project_counts[(cat, div)] += 1
        return project_counts

    @staticmethod
    def get_judge_counts_by_group() -> dict:
        judge_counts = defaultdict(lambda: 0)
        queryset = Judge.objects.filter(user__is_active=True)\
                                .prefetch_related('categories', 'divisions')
        for judge in queryset:
            for cat, div in BulkAssignmentTests.judge_group_iterator(judge):
                judge_counts[(cat, div)] += 1

        return judge_counts

    @classmethod
    def get_minimum_num_projects_by_group(cls) -> dict:
        project_minimums = cls.get_project_counts_by_group()
        for k, v in project_minimums.items():
            project_minimums[k] = min(v, cls.min_num_projects)
        return project_minimums

    @classmethod
    def get_minimum_num_judges_by_group(cls) -> dict:
        judge_minimums = cls.get_judge_counts_by_group()
        for k, v in judge_minimums.items():
            judge_minimums[k] = min(v, cls.min_num_judges)
        return judge_minimums


class BulkJudgeAssignmentTests(BulkAssignmentTests):
    fixtures = BulkAssignmentTests.fixtures
    fixtures.append('judges.json')

    @classmethod
    def setUpClass(cls) -> None:
        super(BulkJudgeAssignmentTests, cls).setUpClass()
        cls.load_fixture('projects_small.json')

    def test_within_bounds(self):
        self.assertWithinBounds()


class BulkProjectAssignmentTests(BulkAssignmentTests):
    fixtures = BulkAssignmentTests.fixtures
    fixtures.append('projects_small.json')

    @classmethod
    def setUpClass(cls) -> None:
        super(BulkProjectAssignmentTests, cls).setUpClass()
        cls.load_fixture('judges.json')

    def test_within_bounds(self):
        self.assertWithinBounds()
