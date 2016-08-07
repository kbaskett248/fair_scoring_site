from django.core.management.base import BaseCommand, CommandError

from fair_categories.models import Division, Category, Subcategory, Ethnicity


CATEGORIES = [
    ('Physical Sciences',
     [('CHEM', 'Chemistry'),
      ('EAEV', 'Earth and Environmental Sciences'),
      ('EBED', 'Embedded Systems'),
      ('EGCH', 'Energy: Chemical'),
      ('EGPH', 'Energy: Physical'),
      ('ENMC', 'Engineering Mechanics'),
      ('ENEV', 'Environmental Engineering'),
      ('MATS', 'Materials Science'),
      ('MATH', 'Mathematics'),
      ('PHYS', 'Physics and Astronomy'),
      ('ROBO', 'Robotics and Intelligent Machines'),
      ('SOFT', 'Systems Software')]
     ),
    ('Life Sciences',
     [('ANIM', 'Animal Sciences'),
      ('BEHA', 'Behavioral and Social Sciences'),
      ('BCHM', 'Biochemistry'),
      ('BMED', 'Biomedical and Health Sciences'),
      ('ENBM', 'Biomedical Engineering'),
      ('CELL', 'Cellular and Molecular Biology'),
      ('CBIO', 'Computational Biology and Bioinformatics'),
      ('MCRO', 'Microbiology'),
      ('PLNT', 'Plant Sciences'),
      ('TMED', 'Translational Medical Sciences')]
     )
]

DIVISIONS = [
    'Middle School',
    'High School'
]

ETHNICITIES = [
    'Hispanic',
    'Black',
    'Caucasian'
]


class Command(BaseCommand):
    help = 'Initializes default values for the fair categories'

    def handle(self, *args, **options):
        self.init_categories(CATEGORIES)
        self.init_divisions(DIVISIONS)
        self.init_ethnicities(ETHNICITIES)

    def init_categories(self, categories):
        self.stdout.write('\nInitializing Categories')
        for desc, subcats in categories:
            cat, created = Category.objects.get_or_create(short_description=desc)
            if created:
                self.stdout.write(self.style.SUCCESS('Successfully created Category "%s"' % cat))
            else:
                self.stdout.write(self.style.NOTICE('Category "%s" already exists' % cat))

            for abbrev, scdesc in subcats:
                subcat, created = Subcategory.objects.get_or_create(
                    category=cat, abbreviation=abbrev, short_description=scdesc)
                if created:
                    self.stdout.write(self.style.SUCCESS('\tSuccessfully created Subcategory "%s"' % subcat))
                else:
                    self.stdout.write(self.style.NOTICE('\tSubcategory "%s" already exists' % subcat))

    def init_divisions(self, divisions):
        self.stdout.write('\nInitializing Divisions')
        for desc in divisions:
            div, created = Division.objects.get_or_create(short_description=desc)
            if created:
                self.stdout.write(self.style.SUCCESS('Successfully created Division "%s"' % div))
            else:
                self.stdout.write(self.style.NOTICE('Division "%s" already exists' % div))

    def init_ethnicities(self, ethnicities):
        self.stdout.write('\nInitializing Ethnicities')
        for desc in ethnicities:
            eth, created = Ethnicity.objects.get_or_create(short_description=desc)
            if created:
                self.stdout.write(self.style.SUCCESS('Successfully created Ethnicity "%s"' % eth))
            else:
                self.stdout.write(self.style.NOTICE('Ethnicity "%s" already exists' % eth))
