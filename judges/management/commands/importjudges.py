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

        with open(csv_path, newline='') as csv_file:
            self.read_file(csv_file)

    def read_file(self, csv_file, global_password=None):
        dialect = csv.Sniffer().sniff(csv_file.read(1024))
        csv_file.seek(0)
        reader = csv.DictReader(csv_file, dialect=dialect)
        has_password = 'Password' in reader.fieldnames

        for row in reader:
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
                                row['School'],
                                password)
