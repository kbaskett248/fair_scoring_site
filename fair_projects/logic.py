import csv

from django.core.exceptions import ObjectDoesNotExist

from .models import Project, Student, Teacher
from fair_categories.models import Category, Subcategory, Division, Ethnicity

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
        if int(row['S1 Grade Level']) >= 9:
            div = high_div
        else:
            div = mid_div

        project = create_project(row['Project Title'], row['Project Abstract'], row['Project Category'],
                                 row['Project Subcategory'], div)

        if not project:
            continue

        for sn in range(1, 3):
            create_student(row['S%s First Name' % sn],
                           row['S%s Last Name' % sn],
                           row['S%s Ethnicity' % sn],
                           row['S%s Gender' % sn],
                           row['S%s Teacher' % sn],
                           row['S%s Grade Level' % sn],
                           project)


def create_project(title, abstract, cat_name, subcat_name, division):
    cat = Category.objects.get(short_description__icontains=cat_name)
    try:
        subcat = Subcategory.objects.get(category=cat,
                                         short_description__icontains=subcat_name)
    except ObjectDoesNotExist:
        return None

    project = Project(title=title,
                      abstract=abstract,
                      category=cat,
                      subcategory=subcat,
                      division=division)
    project.save()

    return project

def create_student(first_name, last_name, eth_name, gender, teacher_name, grade_level, project, email=None):
    if not first_name:
        return

    ethnicity, _ = Ethnicity.objects.get_or_create(short_description=eth_name)
    teacher = Teacher.objects.get(user__last_name=teacher_name)

    student, _ = Student.objects.get_or_create(
        first_name=first_name, last_name=last_name,
        defaults={'ethnicity': ethnicity,
                  'gender': gender,
                  'teacher': teacher,
                  'grade_level': grade_level,
                  'project': project}
    )
    if email:
        student.email = email

    student.save()

    return student

