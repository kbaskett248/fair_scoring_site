# Generated by Django 4.1.3 on 2022-11-26 16:56

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("rubrics", "0009_feedbackmodule_markdownfeedbackmodule"),
    ]

    operations = [
        migrations.AlterField(
            model_name="feedbackmodule",
            name="module_type",
            field=models.CharField(
                choices=[("markdown", "Markdown"), ("score_table", "Score Table")],
                max_length=50,
            ),
        ),
        migrations.CreateModel(
            name="ScoreTableFeedbackModule",
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
                ("include_short_description", models.BooleanField(default=True)),
                ("include_long_description", models.BooleanField(default=True)),
                (
                    "table_title",
                    models.CharField(
                        blank=True, max_length=200, verbose_name="Table title"
                    ),
                ),
                (
                    "short_description_title",
                    models.CharField(
                        blank=True,
                        max_length=50,
                        verbose_name="Short description title",
                    ),
                ),
                (
                    "long_description_title",
                    models.CharField(
                        blank=True, max_length=50, verbose_name="Long description title"
                    ),
                ),
                (
                    "score_title",
                    models.CharField(
                        blank=True, max_length=50, verbose_name="Score title"
                    ),
                ),
                (
                    "use_weighted_scores",
                    models.BooleanField(
                        default=False, verbose_name="Use weighted scores"
                    ),
                ),
                (
                    "remove_empty_scores",
                    models.BooleanField(
                        default=True, verbose_name="Remove empty scores"
                    ),
                ),
                (
                    "questions",
                    models.ManyToManyField(
                        limit_choices_to={
                            "question_type__in": (
                                "SCALE",
                                "SINGLE SELECT",
                                "MULTI SELECT",
                            )
                        },
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
