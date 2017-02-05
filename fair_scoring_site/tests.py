from hypothesis.extra.django import TestCase as HypTestCase
from model_mommy import mommy

from fair_categories.models import Category, Subcategory, Division
from fair_projects.models import Project
from fair_scoring_site.admin import AwardRuleForm


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
            self.success_test(trait, 'IS', good_values[0])

        with self.subTest('Validation fails for single {trait} when value does not exist'.format(
                trait=trait)):
            self.failed_test(trait, 'IS', bad_value)

        with self.subTest('Validation succeeds for {trait} IN when single value exists'.format(
                trait=trait)):
            self.success_test(trait, 'IN', good_values[0])

        with self.subTest('Validation fails for {trait} IN when single value does not exist'.format(
                trait=trait)):
            self.failed_test(trait, 'IN', bad_value)

        with self.subTest('Validation succeeds for {trait} IN when all values exist'.format(
                trait=trait)):
            self.success_test(trait, 'IN', ', '.join(good_values))

        with self.subTest('Validation fails for {trait} IN when any value does not exist'.format(
                trait=trait)):
            self.failed_test(trait, 'IN', ', '.join(good_values + [bad_value]))

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
