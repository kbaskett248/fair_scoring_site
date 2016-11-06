import csv
from collections import defaultdict
from functools import reduce
from itertools import product, filterfalse
from operator import ior

from django.contrib.auth.tokens import default_token_generator
from django.core.mail import EmailMultiAlternatives
from django.core.mail import get_connection
from django.db import transaction
from django.db.models import Count, Q, Avg
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from fair_categories.models import Category, Division
from judges.models import Judge
from rubrics.models import Rubric
from .models import Project, JudgingInstance, create_student, create_project, Teacher

IMPORT_DICT_KEYS = ('Timestamp', 'Project Title', 'Project Abstract',
                    'Project Category', 'Project Subcategory', 'Unused1',
                    'Team or Individual', 'S1 First Name', 'S1 Last Name',
                    'S1 Gender', 'S1 Ethnicity', 'S1 Teacher', 'S1 Grade Level',
                    'S2 First Name', 'S2 Last Name', 'S2 Gender',
                    'S2 Ethnicity', 'S2 Teacher', 'S2 Grade Level', 'Unused2',
                    'S3 First Name', 'S3 Last Name', 'S3 Gender',
                    'S3 Ethnicity', 'S3 Teacher', 'S3 Grade Level')


def handle_project_import(file_):
    contents = []
    for chu in file_.chunks():
        contents.append(chu.decode())
    contents = ''.join(contents).split('\r\n')

    dialect = csv.Sniffer().sniff(contents[0])
    reader = csv.DictReader(contents[1:], fieldnames=IMPORT_DICT_KEYS, dialect=dialect)

    process_project_import(reader)


def process_project_import(reader, output_stream=None):
    div_dict = Division.get_grade_div_dict()
    for row in reader:
        try:
            grade = int(row['S1 Grade Level'])
        except ValueError:
            continue
        else:
            div = div_dict[grade]

        project = create_project(row['Project Title'], row['Project Abstract'], row['Project Category'],
                                 row['Project Subcategory'], div, output_stream=output_stream)

        if not project:
            continue

        for sn in range(1, 3):
            create_student(row['S%s First Name' % sn],
                           row['S%s Last Name' % sn],
                           row['S%s Ethnicity' % sn],
                           row['S%s Gender' % sn],
                           row['S%s Teacher' % sn],
                           row['S%s Grade Level' % sn],
                           project,
                           output_stream=output_stream)


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
    #    2. Compute the median and average number of projects assigned to all judges.
    #    3. Compute the max of the median, average and minimum number of projects per judge.
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
    balance_judges(rubric)


def create_judging_instance(judge, project, rubric):
    return JudgingInstance.objects.create(judge=judge, project=project, rubric=rubric)


def assign_new_projects(rubric):
    project_set = Project.objects.annotate(num_judges=Count('judginginstance')) \
        .order_by('num_judges')

    judge_set = Judge.objects.annotate(num_projects=Count('judginginstance'),
                                       num_categories=Count('categories'),
                                       num_divisions=Count('divisions')) \
        .order_by('num_projects', 'num_categories', 'num_divisions')

    for project in project_set.filter(num_judges__lt=get_minimum_judges_per_project()):
        num_judges = get_minimum_judges_per_project() - project.num_judges
        judges = judge_set.filter(categories=project.category,
                                  divisions=project.division)

        for judge in judges.all():
            judge_projects = [ji.project for ji in judge.judginginstance_set.select_related('project').all()]
            if project in judge_projects:
                continue
            else:
                # print('Assigning {0} to {1}'.format(project, judge))
                create_judging_instance(judge, project, rubric)
                num_judges -= 1

                if num_judges <= 0:
                    break


def get_minimum_judges_per_project():
    return 2


def get_minimum_projects_per_judge():
    return 5


def balance_judges(rubric):
    quotients = build_quotient_array()

    judge_set = Judge.objects.annotate(num_projects=Count('judginginstance', distinct=True))
    lower_bound = get_project_balancing_lower_bound(judge_set)

    for judge in judge_set.filter(num_projects__gt=lower_bound).order_by('-num_projects'):
        balance_judge(judge, rubric, judge_set.filter(num_projects__lt=lower_bound).order_by('num_projects'), lower_bound, quotients)


def build_quotient_array():
    class Quotient(object):
        def __init__(self, num_projects, num_judges):
            self.num_projects = num_projects
            self.num_judges = num_judges

        @property
        def projects_per_judge(self):
            return self.num_projects / self.num_judges

        def __str__(self):
            return 'Projects: {0}; Judges: {1}; Quotient: {2}'.format(self.num_projects,
                                                                      self.num_judges,
                                                                      self.projects_per_judge)

        def __repr__(self):
            return self.__str__()

    proj_counts = {(d['category'], d['division']): d['count'] for d in
                   Project.objects.values('category', 'division').annotate(count=Count('category'))}
    judge_counts = {(d['categories'], d['divisions']): d['count'] for d in
                    Judge.objects.values('categories', 'divisions').annotate(count=Count('categories'))}

    quotient_array = defaultdict(dict)
    for cat, div in product(Category.objects.all(), Division.objects.all()):
        quotient_array[cat][div] = Quotient(proj_counts[(cat.pk, div.pk)], judge_counts[(cat.pk, div.pk)])

    return quotient_array


def get_project_balancing_lower_bound(judge_set):
    median = get_median_projects_per_judge(judge_set)
    # print('Median: ', median)
    minimum = get_minimum_projects_per_judge()
    # print('Minimum: ', minimum)
    average = judge_set.aggregate(avg_projects=Avg('num_projects'))['avg_projects']
    # print('Average: ', average)
    return max(median, minimum, average)


def get_median_projects_per_judge(judge_set):
    return median_value(judge_set, 'num_projects')


def median_value(queryset, term):
    count = queryset.count()
    values = queryset.values_list(term, flat=True).order_by(term)
    if count % 2 == 1:
        return values[int(round(count / 2))]
    else:
        return sum(values[count / 2 - 1:count / 2 + 1]) / 2.0


def balance_judge(judge, rubric, possible_judges, lower_bound, quotients):
    # print(judge)
    num_to_reassign = judge.num_projects - lower_bound
    cat_Q = reduce(ior, (Q(categories=cat) for cat in judge.categories.all()))
    div_Q = reduce(ior, (Q(divisions=div) for div in judge.divisions.all()))
    # print(num_to_reassign)

    def sort_value(judging_instance):
        project = judging_instance.project
        return quotients[project.category][project.division].projects_per_judge

    instances = sorted(get_instances_that_can_be_reassigned(judge, rubric), key=sort_value)
    for ji in instances:
        avail_judge = get_available_judge(ji.project, rubric, possible_judges)
        if avail_judge:
            if reassign_project(ji, avail_judge):
                num_to_reassign -= 1

                # for j in possible_judges.filter(cat_Q, div_Q):
                    # print(j, j.num_projects)

                if num_to_reassign <= 0:
                    break
                elif not possible_judges.filter(cat_Q, div_Q).exists():
                    break


def get_instances_that_can_be_reassigned(judge, rubric):
    return filterfalse(lambda x: x.response.has_response,
                       judge.judginginstance_set.filter(response__rubric=rubric)\
                           .select_related('response', 'project'))


def get_available_judge(project, rubric, possible_judges):
    for judge in possible_judges.filter(categories=project.category, divisions=project.division):
        if judge.judginginstance_set.filter(project=project, response__rubric=rubric).exists():
            # The judge has already been assigned this project, so continue
            continue
        else:
            return judge
    return None


@transaction.atomic()
def reassign_project(judging_instance, to_judge):
    # print("Reassigning {0} from {1} to {2}".format(judging_instance.project.number, judging_instance.judge, to_judge))
    new_instance = create_judging_instance(to_judge, judging_instance.project, judging_instance.response.rubric)
    judging_instance.delete()
    return new_instance


def email_teachers(site_name, domain, use_https=False):
    messages = []
    context = {
        'domain': domain,
        'site_name': site_name,
        'protocol': 'https' if use_https else 'http',
    }
    for teacher in get_teachers():
        context.update(
            {'email': teacher.email,
             'uid': urlsafe_base64_encode(force_bytes(teacher.pk)),
             'user': teacher,
             'token': default_token_generator.make_token(teacher)}
        )

        subject = render_to_string('fair_projects/email/teacher_signup_subject.txt', context)
        # Email subject *must not* contain newlines
        subject = ''.join(subject.splitlines())

        body = render_to_string('fair_projects/email/teacher_signup.txt', context)
        html_email = render_to_string('fair_projects/email/teacher_signup.html', context)

        email_message = EmailMultiAlternatives(subject, body, to=[teacher.email])
        email_message.attach_alternative(html_email, 'text/html')

        messages.append(email_message)

    with get_connection() as connection:
        connection.send_messages(messages)


def get_teachers():
    for teacher in Teacher.objects.select_related('user').all():
        if teacher.user.is_superuser:
            continue

        yield teacher.user
