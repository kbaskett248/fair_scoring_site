# -*- coding: utf-8 -*-
# Generated by Django 1.9.9 on 2016-08-14 03:02
from __future__ import unicode_literals

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Choice",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("order", models.PositiveSmallIntegerField(null=True)),
                ("key", models.CharField(max_length=20)),
                ("description", models.CharField(max_length=200)),
            ],
        ),
        migrations.CreateModel(
            name="Question",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("order", models.PositiveSmallIntegerField(null=True)),
                ("short_description", models.CharField(max_length=200)),
                ("long_description", models.TextField(null=True)),
                ("help_text", models.TextField(null=True)),
                (
                    "weight",
                    models.DecimalField(decimal_places=3, max_digits=3, null=True),
                ),
                (
                    "question_type",
                    models.CharField(
                        choices=[
                            ("SCALE", "Scale"),
                            ("SINGLE SELECT", "Single Select"),
                            ("MULTI SELECT", "Multi-Select"),
                            ("LONG TEXT", "Free Text (Long)"),
                        ],
                        max_length=20,
                    ),
                ),
                (
                    "choice_sort",
                    models.CharField(
                        choices=[("A", "Auto"), ("M", "Manual")], max_length=1
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="Rubric",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=200)),
            ],
        ),
        migrations.AddField(
            model_name="question",
            name="rubric",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE, to="rubrics.Rubric"
            ),
        ),
        migrations.AddField(
            model_name="choice",
            name="question",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE, to="rubrics.Question"
            ),
        ),
    ]
