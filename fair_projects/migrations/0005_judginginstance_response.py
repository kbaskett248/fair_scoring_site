# -*- coding: utf-8 -*-
# Generated by Django 1.9.9 on 2016-08-20 21:36
from __future__ import unicode_literals

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("rubrics", "0003_auto_20160817_1847"),
        ("fair_projects", "0004_auto_20160813_2104"),
    ]

    operations = [
        migrations.AddField(
            model_name="judginginstance",
            name="response",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="rubrics.RubricResponse",
            ),
        ),
    ]
