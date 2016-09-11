import csv
import os

from django.core.management.base import BaseCommand, CommandError
from django.core.exceptions import ObjectDoesNotExist

from fair_categories.models import Category, Division
from judges.models import JudgeEducation, JudgeFairExperience, create_judge


class Command(BaseCommand):
    help = 'Imports a csv file of teachers'

    def add_arguments(self, parser):
        parser.add_argument('tsv_path', type=str,
                            help=('Path to a tsv file containing judge information'))
        parser.add_argument('-p', '--password', type=str,
                            help=('Password to assign to each judge. This value will override any password stored '
                                  'in the input file. If no password is specified here, and no password is stored '
                                  'in the input file, then a random password is assigned.'))
        parser.add_argument('-e', '--email', type=str,
                            help=('Email to assign to each judge. This will override any email stored in the input '
                                  'file. Useful for setting up test judges.'))
        parser.add_argument('-P', '--phone', type=str,
                            help=('Phone number to assign to each judge. This will override any email stored in the '
                                  'input file. Useful for setting up test judges.'))

    def handle(self, *args, **options):
        tsv_path = options['tsv_path']
        if not os.path.isfile(tsv_path):
            raise CommandError('File "%s" does not exist' % tsv_path)

        password = options.get('password', default=None)
        email = options.get('email', default=None)
        phone = options.get('phone', default=None)

        with open(tsv_path, newline='') as tsv_file:
            self.read_file(tsv_file, global_password=password, global_email=email, global_phone=phone)

    def read_file(self, csv_file, global_password=None, global_email=None, global_phone=None):
        dialect = csv.Sniffer().sniff(csv_file.read(1024))
        csv_file.seek(0)
        reader = csv.DictReader(csv_file, dialect=dialect)
        has_password = 'Password' in reader.fieldnames
        has_email = 'Email' in reader.fieldnames
        has_phone = 'Phone Number' in reader.fieldnames

        for row in reader:
            categories = []
            for cat in row['Categories'].split(sep=','):
                categories.append(Category.objects.get_or_create(short_description=cat.strip()))

            divisions = []
            for div in row['Divisions'].split(sep=','):
                divisions.append(Division.objects.get_or_create(short_description=div.strip()))

            education = JudgeEducation.objects.get_or_create(short_description=row['Education'])
            fair_exp = JudgeFairExperience.objects.get_or_create(short_description=row['Fair Experience'])

            password = global_password
            if not password and has_password:
                password = row['Password']

            email = global_email
            if not email and has_email:
                email = row['Email']

            phone = global_phone
            if not phone and has_phone:
                phone = row['Phone Number']

            create_judge(row['Username'],
                         email,
                         row['First Name'],
                         row['Last Name'],
                         phone,
                         education,
                         fair_exp,
                         categories,
                         divisions,
                         password=password,
                         output_stream=self.stdout)
