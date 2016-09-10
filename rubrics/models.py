from django.db import models

class Rubric(models.Model):
    name = models.CharField(
        max_length=200)

    def __str__(self):
        return self.name


class Question(models.Model):
    SCALE_TYPE = 'SCALE'
    SINGLE_SELECT_TYPE = 'SINGLE SELECT'
    MULTI_SELECT_TYPE = 'MULTI SELECT'
    LONG_TEXT = 'LONG TEXT'
    TYPES = (
        (SCALE_TYPE, 'Scale'),
        (SINGLE_SELECT_TYPE, 'Single Select'),
        (MULTI_SELECT_TYPE, 'Multi-Select'),
        (LONG_TEXT, 'Free Text (Long)')
    )
    CHOICE_TYPES = (SCALE_TYPE, SINGLE_SELECT_TYPE, MULTI_SELECT_TYPE)

    AUTO_SORT = 'A'
    MANUAL_SORT = 'M'
    SORT_CHOICES = (
        (AUTO_SORT, 'Auto'),
        (MANUAL_SORT, 'Manual')
    )

    rubric = models.ForeignKey(
        'Rubric',
        on_delete=models.CASCADE
    )
    order = models.PositiveSmallIntegerField(null=True, blank=True)
    short_description = models.CharField(
        max_length=200
    )
    long_description = models.TextField(null=True, blank=True)
    help_text = models.TextField(null=True, blank=True)
    weight = models.DecimalField(
        max_digits=3,
        decimal_places=3,
        null=True
    )
    question_type = models.CharField(
        max_length=20,
        choices=TYPES
    )
    choice_sort = models.CharField(
        max_length=1,
        choices=SORT_CHOICES
    )

    ordering = ('rubric', 'order', 'short_description')

    def __init__(self, *args, **kwargs):
        # __init__ is run when objects are retrieved from the database
        # in addition to when they are created.
        super(Question, self).__init__(*args, **kwargs)
        if not self.order:
            self.order = self._get_next_order()
            if self.order:
                self.save()

    def _get_next_order(self):
        try:
            max_order = Question.objects.filter(
                rubric=self.rubric).aggregate(models.Max('order'))['order__max']
        except Rubric.DoesNotExist:
            return

        if max_order:
            return max_order + 1
        else:
            return 1

    def __str__(self):
        return self.short_description

    def show_choices(self):
        return self.question_type and self.question_type in self.CHOICE_TYPES

    def num_choices(self):
        if self.show_choices():
            return self.choice_set.count()
        else:
            return '-'

    def description(self):
        return self.long_description or self.short_description

    def choices(self):
        for choice in self.choice_set.all():
            yield (choice.key, choice.description)


class Choice(models.Model):
    question = models.ForeignKey(
        'Question',
        on_delete=models.CASCADE
    )
    order = models.PositiveSmallIntegerField(null=True, blank=True)
    key = models.CharField(max_length=20)
    description = models.CharField(max_length=200)

    ordering = ('question', 'order', 'key')

    def __init__(self, *args, **kwargs):
        # __init__ is run when objects are retrieved from the database
        # in addition to when they are created.
        super(Choice, self).__init__(*args, **kwargs)
        if not self.order:
            self.order = self._get_next_order()
            if self.order:
                self.save()

    def _get_next_order(self):
        try:
            max_order = Choice.objects.filter(
                question=self.question).aggregate(models.Max('order'))['order__max']
        except Question.DoesNotExist:
            return

        if max_order:
            return max_order + 1
        else:
            return 1

    def __str__(self):
        return self.description


class RubricResponse(models.Model):
    rubric = models.ForeignKey(
        'Rubric',
        on_delete=models.CASCADE
    )

    def save(self, **kwargs):
        super(RubricResponse, self).save(**kwargs)
        if not self.questionresponse_set.all():
            for ques in self.rubric.question_set.all():
                QuestionResponse.objects.create(rubric_response=self, question=ques)

    @property
    def has_response(self):
        return self.questionresponse_set.exclude(choice_response__isnull=True, text_response__isnull=True).exists()


class QuestionResponse(models.Model):
    rubric_response = models.ForeignKey(
        'RubricResponse',
        on_delete=models.CASCADE
    )
    question = models.ForeignKey(
        'Question',
        on_delete=models.CASCADE
    )
    choice_response = models.CharField(
        max_length=20,
        null=True,
        blank=True
    )
    text_response = models.TextField(null=True, blank=True)

    @property
    def question_answered(self):
        return self.choice_response or self.text_response
