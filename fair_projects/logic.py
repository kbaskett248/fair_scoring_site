import csv

from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Count

from .models import Project, Student, Teacher, JudgingInstance
from fair_categories.models import Category, Subcategory, Division, Ethnicity
from judges.models import Judge
from rubrics.models import Rubric

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


def assign_judges():
    # 1. Assign judges to new projects
    #    1. Search for projects with fewer than the minimum number of judges.
    #    2. For each project:
    #       1. Determine the number of judges the project needs.
    #       2. Search for judges that can judge the project's category and division, sorted by the number of projects
    #          ascending. Get the number of judges needed for the project.
    #       3. Assign the judges to the project

    # 2. Switch projects from judges that have too many projects
    #    1. Count the number of projects in each category division group, the number of judges that can judge that
    #       category and division, and calculate their quotient.
    #    2. Compute the median number of projects assigned to all judges.
    #    3. Compute the max of the median and the minimum number of projects per judge.
    #    4. Search for judges that have more than this number of projects assigned
    #    5. For each judge:
    #       1. Compute the number of projects needed to bring the judge down to the number computed above
    #       2. Get a list of the projects for this judge that don't have any responses.
    #       3. Sort the projects by the quotient computed in step 1.
    #       4. Loop through each project until the necessary number of projects have been removed or there are no
    #          judges available to take the projects.
    #          1. Search for judges that could be assigned the project and sort by number of projects, filtered by
    #             judges that have fewer than the number computed above.
    #          2. Remove the project from the first judge and assign it to the new judge.

    rubric = Rubric.objects.get(name='Judging Form')
    assign_new_projects(rubric)

def get_num_project_range():
    return (8, 13)

def create_judging_instance(judge, project, rubric):
    print('Assigning {0} to {1}'.format(project, judge))
    return JudgingInstance.objects.create(judge=judge, project=project, rubric=rubric)


def assign_new_projects(rubric):
    project_set = Project.objects.annotate(num_judges=Count('judginginstance'))\
        .order_by('num_judges')

    judge_set = Judge.objects.annotate(num_projects=Count('judginginstance'),
                                       num_categories=Count('categories'),
                                       num_divisions=Count('divisions'))\
        .order_by('num_projects', 'num_categories', 'num_divisions')

    for project in project_set.filter(num_judges__lt=get_minimum_judges_per_project()):
        num_judges = get_minimum_judges_per_project() - project.num_judges
        judges = judge_set.filter(categories=project.category,
                                  divisions=project.division,
                                  )

        for judge in judges.all():
            judge_projects = [ji.project for ji in judge.judginginstance_set.all()]
            if project in judge_projects:
                continue
            else:
                create_judging_instance(judge, project, rubric)
                num_judges -= 1

                if num_judges <= 0:
                    break


def get_minimum_judges_per_project():
    return 2
