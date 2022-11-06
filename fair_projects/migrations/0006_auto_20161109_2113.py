# -*- coding: utf-8 -*-
# Generated by Django 1.10.2 on 2016-11-10 02:13
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("fair_projects", "0005_judginginstance_response"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="project",
            options={
                "permissions": (("can_view_results", "Can view project results"),)
            },
        ),
        migrations.AlterField(
            model_name="student",
            name="email",
            field=models.EmailField(blank=True, max_length=254, null=True),
        ),
    ]
