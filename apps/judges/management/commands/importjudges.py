import csv
import os

from django.core.management.base import BaseCommand, CommandError

from apps.fair_categories.models import Category, Division
from apps.judges.models import JudgeEducation, JudgeFairExperience, create_judge


class DefaultDictReader(csv.DictReader):
    def __init__(self, *args, defaults=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.defaults = defaults

    def __next__(self):
        result = super().__next__()
        if self.defaults:
            for key, value in self.defaults.items():
                if key not in result:
                    result[key] = value
        return result


class JudgeData:
    def __init__(self, **kwargs):
        self.row_data = kwargs
        self.email = self.row_data["Email"]
        self.first_name = self.row_data["First Name"]
        self.last_name = self.row_data["Last Name"]

    def items_from_list(self, key):
        return [item.strip() for item in self.row_data[key].split(",")]

    @property
    def categories(self) -> list:
        return [
            Category.objects.get_or_create(short_description=cat)[0]
            for cat in self.items_from_list("Categories")
        ]

    @property
    def divisions(self) -> list:
        return [
            Division.objects.get_or_create(short_description=div)[0]
            for div in self.items_from_list("Divisions")
        ]

    @property
    def username(self) -> str:
        if "Username" in self.row_data:
            return self.row_data["Username"]

        return (self.first_name[0] + self.last_name).lower()

    @property
    def password(self):
        if "Password" in self.row_data:
            return self.row_data["Password"]

        return None

    @property
    def phone(self) -> str:
        if "Phone" in self.row_data:
            return self.row_data["Phone"]

        return None

    @property
    def education(self) -> JudgeEducation:
        return JudgeEducation.objects.get_or_create(
            short_description=self.row_data["Education"]
        )[0]

    @property
    def experience(self) -> JudgeFairExperience:
        return JudgeFairExperience.objects.get_or_create(
            short_description=self.row_data["Fair Experience"]
        )[0]

    def __str__(self) -> str:
        return f"{self.first_name} {self.last_name} ({self.username})"


class Command(BaseCommand):
    help = "Imports a csv file of teachers"  # noqa: A003

    def add_arguments(self, parser):
        parser.add_argument(
            "tsv_path",
            type=str,
            help=("Path to a tsv file containing judge information"),
        )
        parser.add_argument(
            "-p",
            "--password",
            type=str,
            help=(
                "Password to assign to each judge. This value will override any "
                "password stored in the input file. If no password is specified here, "
                "and no password is stored in the input file, then a random password "
                "is assigned."
            ),
        )
        parser.add_argument(
            "-e",
            "--email",
            type=str,
            help=(
                "Email to assign to each judge. This will override any email stored "
                "in the input file. Useful for setting up test judges."
            ),
        )
        parser.add_argument(
            "-P",
            "--phone",
            type=str,
            help=(
                "Phone number to assign to each judge. This will override any email "
                "stored in the input file. Useful for setting up test judges."
            ),
        )

    def handle(self, *args, **options):
        tsv_path = options.pop("tsv_path")
        if not os.path.isfile(tsv_path):
            raise CommandError('File "%s" does not exist' % tsv_path)

        defaults = {}

        def set_if_present(arg: str, default: str) -> None:
            val = options[arg]
            if val:
                defaults[default] = val

        set_if_present("password", "Password")
        set_if_present("email", "Email")
        set_if_present("phone", "Phone")

        with open(tsv_path, newline="") as tsv_file:
            self.read_file(tsv_file, defaults=defaults)

    def read_file(self, csv_file, defaults=None):
        if defaults is None:
            defaults = {}
        dialect = csv.Sniffer().sniff(csv_file.read(1024))
        csv_file.seek(0)
        reader = DefaultDictReader(csv_file, dialect=dialect, defaults=defaults)

        for row in reader:
            self.process_row(row)

    def process_row(self, row_data):
        judge_data = JudgeData(**row_data)

        create_judge(
            judge_data.username,
            judge_data.email,
            judge_data.first_name,
            judge_data.last_name,
            judge_data.phone,
            judge_data.education,
            judge_data.experience,
            judge_data.categories,
            judge_data.divisions,
            password=judge_data.password,
            output_stream=self.stdout,
        )
