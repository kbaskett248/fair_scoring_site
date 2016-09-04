import csv
import os

from django.core.management.base import BaseCommand, CommandError
from django.core.exceptions import ObjectDoesNotExist

from fair_categories.models import Category, Division
from judges.models import JudgeEducation, JudgeFairExperience, create_judge


class Command(BaseCommand):
    help = 'Imports a csv file of teachers'

    def add_arguments(self, parser):
        parser.add_argument('csv_path', type=str)
        parser.add_argument('-p', '--password', type=str)

    def handle(self, *args, **options):
        csv_path = options['csv_path']
        if not os.path.isfile(csv_path):
            raise CommandError('File "%s" does not exist')

        password = options.get('password', default=None)

        with open(csv_path, newline='') as csv_file:
            self.read_file(csv_file, password)

    def read_file(self, csv_file, global_password=None):
        dialect = csv.Sniffer().sniff(csv_file.read(1024))
        csv_file.seek(0)
        reader = csv.DictReader(csv_file, dialect=dialect)
        has_password = 'Password' in reader.fieldnames

        for row in reader:
            categories = []
            for cat in row['Categories'].split(sep=','):
                categories.append(Category.objects.get_or_create(short_description=cat.strip()))

            divisions = []
            for div in row['Divisions'].split(sep=','):
                divisions.append(Division.objects.get_or_create(short_description=div.strip()))

            education = JudgeEducation.objects.get_or_create(short_description=row['Education'])
            fair_exp = JudgeFairExperience.objects.get_or_create(short_description=row['Fair Experience'])

            if global_password:
                password = global_password
            elif has_password:
                password = row['Password']
            else:
                password = None

            create_judge(row['Username'],
                         row['Email'],
                         row['First Name'],
                         row['Last Name'],
                         row['Phone Number'],
                         education,
                         fair_exp,
                         categories,
                         divisions,
                         password=password,
                         output_stream=self.stdout)
