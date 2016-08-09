import csv
import os

from django.contrib.auth.models import User, Group
from django.core.management.base import BaseCommand, CommandError
from django.core.exceptions import ObjectDoesNotExist


class Command(BaseCommand):
    help = 'Imports a csv file of teachers'

    def add_arguments(self, parser):
        parser.add_argument('csv_path', type=str)

    def handle(self, *args, **options):
        csv_path = options['csv_path']
        if not os.path.isfile(csv_path):
            raise CommandError('File "%s" does not exist')

        self.group = Group.objects.get(name='Teachers')
        with open(csv_path, newline='') as csv_file:
            self.read_file(csv_file)

    def read_file(self, csv_file):
        dialect = csv.Sniffer().sniff(csv_file.read(1024))
        csv_file.seek(0)
        reader = csv.DictReader(csv_file, dialect=dialect)
        has_password = 'Password' in reader.fieldnames

        for row in reader:
            if has_password:
                password = row['Password']
            else:
                password = None
            self.create_teacher(row['Username'],
                                row['Email'],
                                row['First Name'],
                                row['Last Name'],
                                password)

    def create_teacher(self, username, email, first_name, last_name, password=None):
        try:
            User.objects.get(username=username)
        except ObjectDoesNotExist:
            pass
        else:
            self.stdout.write(self.style.NOTICE('Teacher %s already exists' % username))
            return

        if not password:
            password = User.objects.make_random_password()
        teacher = User.objects.create_user(username, email, password)
        teacher.first_name = first_name
        teacher.last_name = last_name
        teacher.groups.add(self.group)
        teacher.save()
        self.stdout.write(self.style.SUCCESS('Created new teacher %s' % teacher))
