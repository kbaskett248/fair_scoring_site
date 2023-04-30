from django.core.exceptions import ValidationError
from django.test import TestCase
from model_bakery import baker

from apps.rubrics.forms import ChoiceForm, QuestionForm
from apps.rubrics.models.rubric import Choice, Question, Rubric


class QuestionFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.rubric = baker.make(Rubric)  # type: Rubric
        cls.data = {
            "rubric": cls.rubric.pk,
            "order": 1,
            "short_description": "Test Question",
            "long_description": "This question is very important",
            "help_text": "This is help text for the question",
            "weight": 0,
            "question_type": Question.SCALE_TYPE,
            "choice_sort": Question.MANUAL_SORT,
            "required": True,
        }
        data = cls.data.copy()
        data["rubric"] = cls.rubric
        cls.question = Question.objects.create(**data)  # type: Question

    def get_test_data_and_form(
        self, updated_data: dict, instance: Question | None = None
    ) -> tuple:
        data = self.data.copy()
        if updated_data:
            data.update(updated_data)
        form = QuestionForm(data, instance=instance)
        return data, form

    def success_test(self, instance: Question | None = None, **updated_data):
        data, form = self.get_test_data_and_form(updated_data, instance=instance)
        self.assertTrue(form.is_valid())
        question = form.save(commit=False)
        for key, value in data.items():
            if key == "rubric":
                self.assertEqual(value, question.rubric.pk)
            else:
                self.assertEqual(value, getattr(question, key, None))

    def failed_test(self, instance: Question | None = None, **updated_data):
        _, form = self.get_test_data_and_form(updated_data, instance=instance)
        self.assertFalse(form.is_valid())
        with self.assertRaises(ValueError):
            form.save(commit=False)

    def test_valid_data(self):
        self.success_test()

    def test_invalid_question_type(self):
        self.failed_test(question_type="invalid question type")

    def test_invalid_sort(self):
        self.failed_test(choice_sort="Q")

    def test_negative_weight(self):
        self.failed_test(weight=-0.5)

    def test_weight_with_non_choice_type(self):
        self.failed_test(weight=0.5, question_type=Question.LONG_TEXT)

    def test_instance_with_numeric_choices_and_zero_weight(self):
        self.question.weight = 1
        self.question.save()
        baker.make(Choice, question=self.question, key="1")
        self.success_test(instance=self.question, weight=0)

    def test_instance_with_numeric_choices_and_positive_weight(self):
        self.question.weight = 0
        self.question.save()
        baker.make(Choice, question=self.question, key="1")
        self.success_test(instance=self.question, weight=1)

    def test_instance_with_non_numeric_choices_and_zero_weight(self):
        self.question.weight = 0
        self.question.save()
        baker.make(Choice, question=self.question, key="test")
        self.success_test(instance=self.question, weight=0)

    def test_instance_with_non_numeric_choices_and_positive_weight(self):
        self.question.weight = 0
        self.question.save()
        baker.make(Choice, question=self.question, key="test")
        self.failed_test(instance=self.question, weight=1)


class ChoiceFormTests(TestCase):
    def setUp(self):
        self.question = baker.make(Question)  # type: Question

    def update_question(self, question_type, weight):
        self.question.question_type = question_type
        self.question.weight = weight
        self.question.save()

    def success_test(self, data):
        form = ChoiceForm(data)
        self.assertTrue(form.is_valid())
        choice = form.save()
        self.assertEqual(choice.order, data["order"])
        self.assertEqual(choice.key, data["key"])
        self.assertEqual(choice.description, data["description"])

    def failed_test(self, data):
        form = ChoiceForm(data)
        self.assertFalse(form.is_valid())
        with self.assertRaises(ValueError):
            form.save()

    def test_scale_question_with_positive_weight(self):
        self.update_question(Question.SCALE_TYPE, 1.000)

        data = {
            "question": self.question.pk,
            "order": 1,
            "key": "1",
            "description": "description",
        }
        self.success_test(data)

        data = {
            "question": self.question.pk,
            "order": 2,
            "key": "key",
            "description": "description",
        }
        self.failed_test(data)

    def test_scale_question_with_zero_weight(self):
        self.update_question(Question.SCALE_TYPE, 0)

        data = {
            "question": self.question.pk,
            "order": 1,
            "key": "1",
            "description": "description",
        }
        self.success_test(data)

        data = {
            "question": self.question.pk,
            "order": 2,
            "key": "key",
            "description": "description",
        }
        self.success_test(data)

    def test_single_select_question_with_positive_weight(self):
        self.update_question(Question.SINGLE_SELECT_TYPE, 1.000)

        data = {
            "question": self.question.pk,
            "order": 1,
            "key": "1",
            "description": "description",
        }
        self.success_test(data)

        data = {
            "question": self.question.pk,
            "order": 2,
            "key": "key",
            "description": "description",
        }
        self.failed_test(data)

    def test_single_select_question_with_zero_weight(self):
        self.update_question(Question.SINGLE_SELECT_TYPE, 0)

        data = {
            "question": self.question.pk,
            "order": 1,
            "key": "1",
            "description": "description",
        }
        self.success_test(data)

        data = {
            "question": self.question.pk,
            "order": 2,
            "key": "key",
            "description": "description",
        }
        self.success_test(data)

    def test_multi_select_question_with_positive_weight(self):
        self.update_question(Question.MULTI_SELECT_TYPE, 1.000)

        data = {
            "question": self.question.pk,
            "order": 1,
            "key": "1",
            "description": "description",
        }
        self.success_test(data)

        data = {
            "question": self.question.pk,
            "order": 2,
            "key": "key",
            "description": "description",
        }
        self.failed_test(data)

    def test_multi_select_question_with_zero_weight(self):
        self.update_question(Question.MULTI_SELECT_TYPE, 0)

        data = {
            "question": self.question.pk,
            "order": 1,
            "key": "1",
            "description": "description",
        }
        self.success_test(data)

        data = {
            "question": self.question.pk,
            "order": 2,
            "key": "key",
            "description": "description",
        }
        self.success_test(data)

    def test_long_text_question_with_positive_weight(self):
        with self.assertRaises(ValidationError):
            self.update_question(Question.LONG_TEXT, 1.000)

    def test_long_text_question_with_zero_weight(self):
        self.update_question(Question.LONG_TEXT, 0)

        data = {
            "question": self.question.pk,
            "order": 1,
            "key": "1",
            "description": "description",
        }
        self.failed_test(data)

        data = {
            "question": self.question.pk,
            "order": 2,
            "key": "key",
            "description": "description",
        }
        self.failed_test(data)
