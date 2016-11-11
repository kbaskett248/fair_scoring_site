from django.test import TestCase
from hypothesis import given
from hypothesis.extra.django import TestCase as HypTestCase
from hypothesis.strategies import text
from model_mommy import mommy

from awards.models import Award, AwardRule, Operator, Is, Greater


def make_Award(**kwargs) -> Award:
    return mommy.make(Award, **kwargs)


def make_AwardRule(**kwargs) -> AwardRule:
    return mommy.make(AwardRule, **kwargs)


class AwardTests(TestCase):
    def test_award_str(self):
        award = make_Award()
        self.assertEqual(str(award), award.name)


class AwardRuleTests(HypTestCase):
    def setUp(self):
        self.award = make_Award()

    def test_award_rule_str(self):
        rule = make_AwardRule()
        self.assertEqual(str(rule), '{trait} {0} {value}'.format(rule.operator.display, **rule.__dict__))

    @given(text(max_size=20))
    def test_operator_raises_error_with_invalid_operator_name(self, operator_name):
        with self.assertRaises(ValueError):
            rule = make_AwardRule(operator_name=operator_name)

    def test_operator_is_Operator_instance(self):
        for op in AwardRule.OPERATORS:
            rule = make_AwardRule(operator_name=op.internal)
            self.assertIsInstance(rule.operator, Operator)

    def test_changing_operator_name_also_changes_operator(self):
        rule = make_AwardRule(operator_name=Is.internal)
        self.assertIsInstance(rule.operator, Is)

        rule.operator_name = Greater.internal
        self.assertIsInstance(rule.operator, Greater)
