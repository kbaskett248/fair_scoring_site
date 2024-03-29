# -*- coding: utf-8 -*-
# Generated by Django 1.9.9 on 2016-08-17 22:47
from __future__ import unicode_literals

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("rubrics", "0002_auto_20160813_2316"),
    ]

    operations = [
        migrations.CreateModel(
            name="QuestionResponse",
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
                (
                    "choice_response",
                    models.CharField(blank=True, max_length=20, null=True),
                ),
                ("text_response", models.TextField(blank=True, null=True)),
                (
                    "question",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="rubrics.Question",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="RubricResponse",
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
                (
                    "rubric",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="rubrics.Rubric",
                    ),
                ),
            ],
        ),
        migrations.AddField(
            model_name="questionresponse",
            name="rubric_response",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                to="rubrics.RubricResponse",
            ),
        ),
    ]
