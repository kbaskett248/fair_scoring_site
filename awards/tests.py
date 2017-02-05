from collections import namedtuple

from django.core.exceptions import ValidationError
from django.test import TestCase
from hypothesis import assume
from hypothesis import example
from hypothesis import given
from hypothesis.extra.django import TestCase as HypTestCase
from hypothesis.searchstrategy import SearchStrategy
from hypothesis.strategies import text, one_of, integers, booleans, floats, lists
from model_mommy import mommy

from awards.admin import AwardRuleForm
from awards.logic import InstanceBase
from awards.models import Award, AwardRule, Is, Greater, NotIn


def make_Award(**kwargs) -> Award:
    return mommy.make(Award, **kwargs)


def make_AwardRule(**kwargs) -> AwardRule:
    return mommy.make(AwardRule, **kwargs)


def sane_text(min_size=None, max_size=None, average_size=None) -> SearchStrategy:
    return text(alphabet=[chr(i) for i in range(33, 126)],
                min_size=min_size, max_size=max_size, average_size=average_size)


def text_lists(min_size=None, max_size=None, average_size=None) -> SearchStrategy:
    return lists(elements=sane_text(), min_size=min_size, max_size=max_size,
                 average_size=average_size)


def numeric_strings(min_value=None, max_value=None) -> SearchStrategy:
    return one_of(
        integers(min_value=min_value, max_value=max_value),
        floats(min_value=min_value, max_value=max_value)
    ).map(str)


def instance_values() -> SearchStrategy:
    return one_of(
        sane_text(max_size=300, average_size=10),
        integers(),
        booleans(),
        floats(),
        numeric_strings()
    )


class AwardTests(TestCase):
    class TestInstance(InstanceBase):
        def __init__(self, trait_a, trait_b):
            super(AwardTests.TestInstance, self).__init__()
            self.trait_a = trait_a
            self.trait_b = trait_b

    def setUp(self):
        self.award1 = make_Award(name='Award 1',
                                 award_order=1,
                                 award_count=1)
        make_AwardRule(award=self.award1,
                       trait='trait_a',
                       operator_name='IS',
                       value='A')
        make_AwardRule(award=self.award1,
                       trait='trait_b',
                       operator_name='IS',
                       value='A')
        self.award2 = make_Award(name='Award 2',
                                 award_order=2,
                                 award_count=1,
                                 exclude_awards=[self.award1])
        make_AwardRule(award=self.award2,
                       trait='trait_a',
                       operator_name='IS',
                       value='B')
        make_AwardRule(award=self.award2,
                       trait='trait_b',
                       operator_name='IS',
                       value='B')

    def test_award_str(self):
        self.assertEqual(str(self.award1), self.award1.name)

    def test_assign_single_instance(self):
        with self.subTest('Award 1 is assigned ans award 2 is not'):
            instance = self.TestInstance('A', 'A')
            instances = [instance]
            self.award1.assign(instances)
            self.assertIn(self.award1, instance.awards)

            self.award2.assign(instances)
            self.assertNotIn(self.award2, instance.awards)

        with self.subTest('Award 2 is assigned and Award 1 is not'):
            instance = self.TestInstance('B', 'B')
            instances = [instance]
            self.award1.assign(instances)
            self.assertNotIn(self.award1, instance.awards)

            self.award2.assign(instances)
            self.assertIn(self.award2, instance.awards)

        with self.subTest('Neither Award 1 nor Award 2 is assigned'):
            instance = self.TestInstance('A', 'B')
            instances = [instance]
            self.award1.assign(instances)
            self.assertNotIn(self.award1, instance.awards)

            self.award2.assign(instances)
            self.assertNotIn(self.award2, instance.awards)


class AwardRuleTests(HypTestCase):
    def setUp(self):
        self.award = make_Award()

    def test_award_rule_str(self):
        rule = make_AwardRule()
        self.assertEqual(str(rule), '{trait} {0} {value}'.format(rule.operator.display, **rule.__dict__))

    @given(text(min_size=1, max_size=20))
    def test_operator_raises_error_with_invalid_operator_name(self, operator_name):
        with self.assertRaises(ValueError):
            rule = make_AwardRule(operator_name=operator_name)

    def test_operator_is_Operator_instance(self):
        for op in AwardRule.OPERATORS:
            rule = make_AwardRule(operator_name=op.internal)
            self.assertEqual(rule.operator, op)

    def test_changing_operator_name_also_changes_operator(self):
        rule = make_AwardRule(operator_name=Is.internal)
        self.assertEqual(rule.operator, Is)

        rule.operator_name = Greater.internal
        self.assertEqual(rule.operator, Greater)

        rule.operator = NotIn
        self.assertEqual(rule.operator, NotIn)

    def generic_operator_test(self, operator_name, rule_value, instance_value, expected_result, test=None):
        TestInstance = namedtuple('TestInstance', ('test_trait'))
        if not test:
            test = self.assertIs
        rule = make_AwardRule(trait='test_trait', value=rule_value, operator_name=operator_name)
        instance = TestInstance(instance_value)
        test(rule.allow_instance(instance), expected_result)

    @given(sane_text(max_size=300, average_size=10), instance_values())
    def test_allow_instance_Is(self, rule_value: str, instance_value):
        self.generic_operator_test('IS', rule_value, instance_value, rule_value == str(instance_value))
        self.generic_operator_test('IS', rule_value, rule_value, True)
        self.generic_operator_test('IS', str(instance_value), instance_value, True)

    @given(sane_text(max_size=300, average_size=10), instance_values())
    def test_allow_instance_IsNot(self, rule_value: str, instance_value):
        self.generic_operator_test('IS_NOT', rule_value, instance_value, rule_value != str(instance_value))
        self.generic_operator_test('IS_NOT', rule_value, rule_value, False)
        self.generic_operator_test('IS_NOT', str(instance_value), instance_value, False)

    @given(sane_text(max_size=300, average_size=10, min_size=1), instance_values())
    def test_allow_instance_Greater_string(self, rule_value: str, instance_value):
        if isinstance(instance_value, bool):
            test_value = instance_value > bool(rule_value)
        else:
            try:
                test_value = float(instance_value) > float(rule_value)
            except ValueError:
                test_value = str(instance_value) > rule_value

        self.generic_operator_test('GREATER', rule_value, instance_value, test_value)
        self.generic_operator_test('GREATER', rule_value, rule_value, False)
        if not isinstance(instance_value, bool):
            self.generic_operator_test('GREATER', str(instance_value), instance_value, False)

    @given(numeric_strings(min_value=-40000, max_value=40000), floats(min_value=-40000, max_value=40000))
    def test_allow_instance_Greater_numeric(self, rule_value: str, instance_value: float):
        self.generic_operator_test('GREATER', rule_value, instance_value, instance_value > float(rule_value))
        self.generic_operator_test('GREATER', rule_value, rule_value, False)
        self.generic_operator_test('GREATER', str(instance_value), instance_value, False)
        self.generic_operator_test('GREATER', rule_value, '1' + rule_value, True)

    @given(sane_text(max_size=300, average_size=10, min_size=1), instance_values())
    def test_allow_instance_Less_string(self, rule_value: str, instance_value):
        if isinstance(instance_value, bool):
            test_value = instance_value < bool(rule_value)
        else:
            try:
                test_value = float(instance_value) < float(rule_value)
            except ValueError:
                test_value = str(instance_value) < rule_value

        self.generic_operator_test('LESS', rule_value, instance_value, test_value)
        self.generic_operator_test('LESS', rule_value, rule_value, False)
        if not isinstance(instance_value, bool):
            self.generic_operator_test('LESS', str(instance_value), instance_value, False)

    @given(numeric_strings(min_value=-40000, max_value=40000), floats(min_value=-40000, max_value=40000))
    def test_allow_instance_Less_numeric(self, rule_value: str, instance_value: float):
        self.generic_operator_test('LESS', rule_value, instance_value, instance_value < float(rule_value))
        self.generic_operator_test('LESS', rule_value, rule_value, False)
        self.generic_operator_test('LESS', str(instance_value), instance_value, False)
        self.generic_operator_test('LESS', '1' + rule_value, rule_value, True)

    @given(text_lists(max_size=50, average_size=10), instance_values())
    @example([], "")
    def test_allow_instance_In(self, rule_value: list, instance_value):
        assume(not (len(rule_value) == 1 and rule_value[0] == ''))
        assume(',' not in str(instance_value))
        assume(',' not in ''.join(rule_value))

        formatted_rule_value = ','.join(rule_value)
        self.generic_operator_test('IN', formatted_rule_value, instance_value, instance_value in rule_value)

        rule_value.append(str(instance_value))
        rule_value.append('something else')
        formatted_rule_value = ','.join(rule_value)
        self.generic_operator_test('IN', formatted_rule_value, instance_value, True)

        self.generic_operator_test('IN', 'happy,days', instance_value, False)

    @given(text_lists(max_size=50, average_size=10), instance_values())
    def test_allow_instance_NotIn(self, rule_value: list, instance_value):
        assume(not (len(rule_value) == 1 and rule_value[0] == ''))
        assume(',' not in str(instance_value))
        assume(',' not in ''.join(rule_value))

        formatted_rule_value = ','.join(rule_value)
        self.generic_operator_test('NOT_IN', formatted_rule_value, instance_value, instance_value not in rule_value)

        rule_value.append(str(instance_value))
        rule_value.append('something else')
        formatted_rule_value = ','.join(rule_value)
        self.generic_operator_test('NOT_IN', formatted_rule_value, instance_value, False)

        self.generic_operator_test('NOT_IN', 'happy,days', instance_value, True)


class AwardRuleFormTests(HypTestCase):
    class TestForm(AwardRuleForm):
        traits = ('test_trait', 'other_trait')

        def validate_test_trait(self, trait=None, operator_name=None, value=None):
            if value == 'Error':
                raise ValidationError('The trait has an invalid value')

    @classmethod
    def setUpClass(cls):
        super(AwardRuleFormTests, cls).setUpClass()
        cls.data = {'trait': 'test_trait',
                    'operator_name': 'IS',
                    'value': 'Valid Data'}

    def get_form(self, **updated_data):
        data = self.data.copy()
        data.update(updated_data)
        return self.TestForm(data)

    def test_form_valid_for_valid_data(self):
        form = self.get_form()
        self.assertTrue(form.is_valid())

    def test_form_invalid_for_invalid_data(self):
        form = self.get_form(value='Error')
        self.assertFalse(form.is_valid())

    def test_form_valid_for_invalidated_data(self):
        with self.subTest('Test with Valid Data'):
            form = self.get_form(trait='other_trait')
            self.assertTrue(form.is_valid())

        with self.subTest('Test with Error'):
            form = self.get_form(trait='other_trait', value='Error')
            self.assertTrue(form.is_valid())

    def test_form_validation_trims_spaces_from_list(self):
        with self.subTest('IN operator'):
            form = self.get_form(operator_name='IN', value='one , two, three')
            self.assertTrue(form.is_valid())
            self.assertEqual(form.cleaned_data['value'], 'one,two,three')
        with self.subTest('NOT_IN operator'):
            form = self.get_form(operator_name='NOT_IN', value='one , two, three')
            self.assertTrue(form.is_valid())
            self.assertEqual(form.cleaned_data['value'], 'one,two,three')

    def test_form_validation_does_not_change_non_list(self):
        with self.subTest('IN operator'):
            form = self.get_form(operator_name='IN', value='one')
            self.assertTrue(form.is_valid())
            self.assertEqual(form.cleaned_data['value'], 'one')
        with self.subTest('NOT_IN operator'):
            form = self.get_form(operator_name='NOT_IN', value='one')
            self.assertTrue(form.is_valid())
            self.assertEqual(form.cleaned_data['value'], 'one')

    def test_form_validation_does_not_change_non_list_operators(self):
        form = self.get_form(value='one , two, three')
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['value'], 'one , two, three')

    def test_form_validation_prevents_invalid_traits(self):
        form = self.get_form(trait='invalid_trait')
        self.assertFalse(form.is_valid())

    def test_form_validation_removes_empty_values(self):
        form = self.get_form(operator_name='IN', value='one, , two, three, ')
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['value'], 'one,two,three')
