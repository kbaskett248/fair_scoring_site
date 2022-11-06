import csv
import os

from django.core.management.base import BaseCommand, CommandError

from fair_projects.logic import process_project_import


class Command(BaseCommand):
    help = "Imports a csv file of projects"

    def add_arguments(self, parser):
        parser.add_argument("csv_path", type=str)

    def handle(self, *args, **options):
        csv_path = options["csv_path"]
        if not os.path.isfile(csv_path):
            raise CommandError('File "%s" does not exist')

        with open(csv_path, newline="") as csv_file:
            self.read_file(csv_file)

    def read_file(self, csv_file):
        dialect = csv.Sniffer().sniff(csv_file.read(2048))
        csv_file.seek(0)
        reader = csv.DictReader(csv_file, dialect=dialect)

        process_project_import(reader, output_stream=self.stdout)
