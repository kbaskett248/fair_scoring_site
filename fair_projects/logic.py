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
    reader = csv.DictReader(file_, fieldnames = IMPORT_DICT_KEYS,
                            delimiter='\t')
    for div in Division.objects.all():
        if div.short_description == 'Middle School':
            mid_div = div
        elif div.short_description == 'High School':
            high_div = div

    divisions = [(div.short_description, div) for div in Division.objects.all()]
    divisions.sort()
    categories = [(cat.short_description, cat) for cat in Category.objects.all()]
    categories.sort()

    init_values = defaultdict(dict)
    default_min = 1000
    for div, cat in itertools.product(divisions, categories):
        max_proj_number = int(Project.objects.filter(division=div[1], category=cat[1]).aggregate(Max('number'))['number_max'])
        if max_proj_number:
            init_values[div[0]][cat[0]] = max_proj_number
        else:
            init_values[div[0]][cat[0]] = default_min
        default_min += 1000


    for row in reader:
        cat = Category.objects.filter(short_description=row['Project Category'])[0]
        subcat = Subcategory.objects.filter(category=cat,
                                            short_description=row['Project Subcategory'])[0]

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

