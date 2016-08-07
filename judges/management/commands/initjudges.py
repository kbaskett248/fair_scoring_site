from django.core.management.base import BaseCommand, CommandError

from judges.models import JudgeFairExperience, JudgeEducation


FAIR_EXPERIENCES = [
    ('First time', 'This is my first time judging'),
    ('1-3 years', '1 - 3 years'),
    ('4-6 years', '4 - 6 years'),
    ('7-9 years', '7 - 9 years'),
    ('10+ years', '10 years or more')
]

EDUCATIONS = [
    ('High School', 'High School'),
    ('Some college', 'Some college (1 - 4 years; no degree)'),
    ("Associate's degree", "Associate’s degree (including occupational or academic degrees)"),
    ("Bachelor's degree", "Bachelor's degree"),
    ("Master's degree", "Master's degree"),
    ("Professional degree", 'Professional school degree (MD, DDC, JD, etc)'),
    ('Doctorate degree', 'Doctorate degree (PhD, EdD, etc)')
]


class Command(BaseCommand):
    help = 'Initializes default database values for the judges app'

    def handle(self, *args, **options):
        self.init_experience(FAIR_EXPERIENCES)
        self.init_education(EDUCATIONS)

    def init_experience(self, experiences):
        self.stdout.write('\nInitializing Judge Fair Experiences')
        for short_desc, long_desc in experiences:
            exp, created = JudgeFairExperience.objects.get_or_create(
                short_description=short_desc, defaults={'long_description': long_desc})
            if created:
                self.stdout.write(self.style.SUCCESS('Successfully created Experience "%s"' % exp))
            else:
                self.stdout.write(self.style.NOTICE('Experience "%s" already exists' % exp))

    def init_education(self, educations):
        self.stdout.write('\nInitializing Judge Educations')
        for short_desc, long_desc in educations:
            educat, created = JudgeEducation.objects.get_or_create(
                short_description=short_desc, defaults={'long_description': long_desc})
            if created:
                self.stdout.write(self.style.SUCCESS('Successfully created Education "%s"' % educat))
            else:
                self.stdout.write(self.style.NOTICE('Education "%s" already exists' % educat))
