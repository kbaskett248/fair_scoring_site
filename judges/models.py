from django.contrib.auth.models import User, Group
from django.core.exceptions import ObjectDoesNotExist
from django.core.validators import RegexValidator
from django.dispatch import Signal
from django.db import models, transaction


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
    post_commit = Signal(providing_args=['instance'])

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
        null=True,
        on_delete=models.SET_NULL
    )
    fair_experience = models.ForeignKey(
        JudgeFairExperience,
        verbose_name='Years of experience',
        help_text=('How many years have you judged science fairs at the '
                   'county level or higher?'),
        null=True,
        on_delete=models.SET_NULL
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
        ordering = ('user__last_name', 'user__first_name')

    class WithUserManager(models.Manager):
        def get_queryset(self):
            return super().get_queryset() \
                          .select_related('user')

    objects = WithUserManager()

    def __str__(self):
        return self.user.first_name + ' ' + self.user.last_name

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        super(Judge, self).save(force_insert=force_insert, force_update=force_update,
                                using=using, update_fields=update_fields)
        transaction.on_commit(lambda: self.post_commit.send(sender=Judge, instance=self))



@transaction.atomic()
def create_judge(username, email, first_name, last_name, phone, education, fair_exp, categories, divisions,
                 password=None, has_device=True, output_stream=None):
    def write_output(message):
        if output_stream:
            output_stream.write(message)

    user, save_user = User.objects.get_or_create(username=username,
                                                 defaults={
                                                     'email': email,
                                                     'first_name': first_name,
                                                     'last_name': last_name
                                                 })
    if save_user:
        if not password:
            password = User.objects.make_random_password()
        user.set_password(password)
    else:
        write_output('Judge user %s already exists' % username)

    judges_group = Group.objects.get(name='Judges')
    if judges_group.pk not in user.groups.all():
        user.groups.add(judges_group.pk)
        save_user = True

    if save_user:
        user.save()

    if save_user:
        try:
            judge = Judge.objects.get(user=user)
        except ObjectDoesNotExist:
            judge = Judge.objects.create(user=user, phone=phone, has_device=has_device, education=education,
                                         fair_experience=fair_exp)
            judge.categories.add(*categories)
            judge.divisions.add(*divisions)
            judge.save()
            write_output('Judge %s created' % username)
            return judge
        else:
            return judge
