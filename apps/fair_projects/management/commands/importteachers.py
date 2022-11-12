import csv
import os

from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand, CommandError

from apps.fair_projects.models import create_teacher


class Command(BaseCommand):
    help = "Imports a csv file of teachers"

    def add_arguments(self, parser):
        parser.add_argument("csv_path", type=str)
        parser.add_argument(
            "-p",
            "--password",
            type=str,
            help=(
                "Password to assign to each teacher. This value will override any password stored "
                "in the input file. If no password is specified here, and no password is stored "
                "in the input file, then a random password is assigned."
            ),
        )
        parser.add_argument(
            "-e",
            "--email",
            type=str,
            help=(
                "Email to assign to each teacher. This will override any email stored in the input "
                "file. Useful for setting up test teachers."
            ),
        )

    def handle(self, *args, **options):
        csv_path = options["csv_path"]
        if not os.path.isfile(csv_path):
            raise CommandError('File "%s" does not exist')

        self.group = Group.objects.get(name="Teachers")

        password = options.get("password", None)
        email = options.get("email", None)
        phone = options.get("phone", None)

        with open(csv_path, newline="") as csv_file:
            self.read_file(
                csv_file,
                global_password=password,
                global_email=email,
                global_phone=phone,
            )

    def read_file(
        self, csv_file, global_password=None, global_email=None, global_phone=None
    ):
        dialect = csv.Sniffer().sniff(csv_file.read(1024))
        csv_file.seek(0)
        reader = csv.DictReader(csv_file, dialect=dialect)
        has_password = "Password" in reader.fieldnames
        has_email = "Email" in reader.fieldnames
        has_phone = "Phone Number" in reader.fieldnames

        for row in reader:
            password = global_password
            if not password and has_password:
                password = row["Password"]

            email = global_email
            if not email and has_email:
                email = row["Email"]

            phone = global_phone
            if not phone and has_phone:
                phone = row["Phone Number"]

            create_teacher(
                row["Username"],
                email,
                row["First Name"],
                row["Last Name"],
                row["School"],
                password,
                output_stream=self.stdout,
            )
