from django.contrib.auth.models import User
from django.core.validators import RegexValidator
from django.db import models


# Create your models here.
class PhoneField(models.CharField):
    phone_regex = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message=("Phone number must be entered in the format: '+999999999'. "
                 "Up to 15 digits allowed."))

    def __init__(self, **options):
        try:
            vals = list(options['validators'])
            vals.append(PhoneField.phone_regex)
        except KeyError:
            vals = [PhoneField.phone_regex]
        finally:
            options['validators'] = vals

        try:
            options['max_length']
        except KeyError:
            options['max_length'] = 15

        super(PhoneField, self).__init__(**options)


class JudgeFairExperience(models.Model):
    short_description = models.CharField(max_length=100)
    long_description = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.short_description


class JudgeEducation(models.Model):
    short_description = models.CharField(max_length=100)
    long_description = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.short_description


class Judge(models.Model):
    user = models.OneToOneField(User,
                                on_delete=models.CASCADE,
                                primary_key=True)
    phone = PhoneField()
    has_device = models.BooleanField(
        verbose_name=('Do you have a smartphone or tablet to use during fair '
                      'judging?'),
        help_text=('This device will be used with our electronic judging '
                   'system.')
    )

    education = models.ForeignKey(
        JudgeEducation,
        verbose_name='Level of education',
        help_text=('Which option best describes your level of education? We '
                   'are required to compile this information for ISEF '
                   'reporting purposes.'),
        null=True
    )
    fair_experience = models.ForeignKey(
        JudgeFairExperience,
        verbose_name='Years of experience',
        help_text=('How many years have you judged science fairs at the '
                   'county level or higher?'),
        null=True
    )

    categories = models.ManyToManyField(
        'fair_categories.Category',
        verbose_name='Which categories are you most comfortable judging?'
    )
    divisions = models.ManyToManyField(
        'fair_categories.Division',
        verbose_name='Which division(s) do you prefer to judge?'
    )

    class Meta:
        permissions = (
            ('is_judge', 'Designates this user as a judge'),
        )

    def __str__(self):
        return self.user.first_name + ' ' + self.user.last_name



