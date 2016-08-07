from collections import defaultdict
import csv
import itertools

from django.db.models import Max

from .models import Project

from fair_categories.models import Category, Subcategory, Division

IMPORT_DICT_KEYS = ('Timestamp', 'Project Title', 'Project Abstract',
                    'Project Category', 'Project Subcategory', 'Unused1',
                    'Team or Individual', 'S1 First Name', 'S1 Last Name',
                    'S1 Gender', 'S1 Ethnicity', 'S1 Teacher', 'S1 Grade Level',
                    'S2 First Name', 'S2 Last Name', 'S2 Gender',
                    'S2 Ethnicity',	'S2 Teacher', 'S2 Grade Level', 'Unused2',
                    'S3 First Name', 'S3 Last Name', 'S3 Gender',
                    'S3 Ethnicity',	'S3 Teacher', 'S3 Grade Level')

def handle_project_import(file_):
    categories = sorted(Category.objects.all(), key=lambda x: x.short_description)
    divisions = sorted(Division.objects.all(), key=lambda x: x.short_description)
    for div in divisions:
        if div.short_description == 'Middle School':
            mid_div = div
        elif div.short_description == 'High School':
            high_div = div

    init_values = defaultdict(dict)
    default_min = 1000
    for div, cat in itertools.product(divisions, categories):
        mpn = Project.objects.filter(division=div, category=cat).aggregate(Max('number'))['number__max']
        if mpn:
            init_values[div.short_description][cat.short_description] = int(mpn)
        else:
            init_values[div.short_description][cat.short_description] = default_min
        default_min += 1000

    contents = []
    for chu in file_.chunks():
        contents.append(chu.decode())
    contents = ''.join(contents).split('\r\n')

    dialect = csv.Sniffer().sniff(contents[0])
    reader = csv.DictReader(contents[1:], fieldnames=IMPORT_DICT_KEYS, dialect=dialect)

    for row in reader:
        # if not row['Project Title']:
        #     continue
        cat = Category.objects.filter(short_description=row['Project Category'])[0]
        try:
            subcat = Subcategory.objects.filter(category=cat,
                                                short_description=row['Project Subcategory'])[0]
        except IndexError:
            subcat = Subcategory(category=cat, short_description='(NEW) ' + row['Project Subcategory'])
            subcat.save()

        if int(row['S1 Grade Level']) >= 9:
            div = high_div
        else:
            div = mid_div

        number = init_values[div.short_description][cat.short_description] + 1
        init_values[div.short_description][cat.short_description] = number

        project = Project(title=row['Project Title'],
                          abstract=row['Project Abstract'],
                          category=cat,
                          subcategory=subcat,
                          division=div,
                          number=number
                          )
        project.save()

