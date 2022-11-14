# -*- coding: utf-8 -*-
# Generated by Django 1.9.9 on 2016-08-14 01:04
from __future__ import unicode_literals

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("fair_projects", "0003_auto_20160323_2121"),
    ]

    operations = [
        migrations.AlterField(
            model_name="student",
            name="project",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="fair_projects.Project",
            ),
        ),
    ]