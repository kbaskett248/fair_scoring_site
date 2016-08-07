from collections import defaultdict
import csv
import itertools

from django.db.models import Max
from django.core.exceptions import ObjectDoesNotExist

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
    for div in Division.objects.all():
        if div.short_description == 'Middle School':
            mid_div = div
        elif div.short_description == 'High School':
            high_div = div

    contents = []
    for chu in file_.chunks():
        contents.append(chu.decode())
    contents = ''.join(contents).split('\r\n')

    dialect = csv.Sniffer().sniff(contents[0])
    reader = csv.DictReader(contents[1:], fieldnames=IMPORT_DICT_KEYS, dialect=dialect)

    for row in reader:
        cat = Category.objects.get(short_description__icontains=row['Project Category'])
        try:
            subcat = Subcategory.objects.get(category=cat,
                                             short_description__icontains=row['Project Subcategory'])
        except ObjectDoesNotExist:
            continue

        if int(row['S1 Grade Level']) >= 9:
            div = high_div
        else:
            div = mid_div

        project = Project(title=row['Project Title'],
                          abstract=row['Project Abstract'],
                          category=cat,
                          subcategory=subcat,
                          division=div
                          )
        project.save()

