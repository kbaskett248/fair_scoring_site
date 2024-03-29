# -*- coding: utf-8 -*-
# Generated by Django 1.10.2 on 2016-11-03 01:42
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("rubrics", "0004_question_required"),
    ]

    operations = [
        migrations.AddField(
            model_name="questionresponse",
            name="last_submitted",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="question",
            name="weight",
            field=models.DecimalField(decimal_places=3, max_digits=4, null=True),
        ),
    ]
