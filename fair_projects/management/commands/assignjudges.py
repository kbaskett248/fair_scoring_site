from django.core.management.base import BaseCommand, CommandError

from fair_projects.logic import assign_judges

class Command(BaseCommand):
    help = 'Assigns projects to judges'

    # def add_arguments(self, parser):
    #     parser.add_argument('csv_path', type=str)

    def handle(self, *args, **options):
        assign_judges()