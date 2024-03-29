# Generated by Django 4.1.3 on 2022-11-26 16:59

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("rubrics", "0011_alter_markdownfeedbackmodule_content"),
    ]

    operations = [
        migrations.AlterField(
            model_name="feedbackmodule",
            name="module_type",
            field=models.CharField(
                choices=[
                    ("markdown", "Markdown"),
                    ("score_table", "Score Table"),
                    ("choice_response_list", "Choice Response List"),
                ],
                max_length=50,
            ),
        ),
        migrations.CreateModel(
            name="ChoiceResponseListFeedbackModule",
            fields=[
                (
                    "base_module",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="rubrics.feedbackmodule",
                    ),
                ),
                (
                    "display_description",
                    models.BooleanField(
                        default=True,
                        help_text="If checked, the choice description is displayed in the list. Otherwise the choice key is displayed.",
                        verbose_name="Display description",
                    ),
                ),
                (
                    "remove_duplicates",
                    models.BooleanField(
                        default=True,
                        help_text="If checked, response choices will only be displayed once, regardless of how many times the response is chosen. Otherwise, choices will be listed once for each time they are chosen.",
                        verbose_name="Remove duplicates",
                    ),
                ),
                (
                    "question",
                    models.ForeignKey(
                        limit_choices_to={
                            "question_type__in": (
                                "SCALE",
                                "SINGLE SELECT",
                                "MULTI SELECT",
                            )
                        },
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        to="rubrics.question",
                    ),
                ),
            ],
            options={
                "abstract": False,
            },
            bases=("rubrics.feedbackmodule",),
        ),
    ]
