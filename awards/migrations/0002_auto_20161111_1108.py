# -*- coding: utf-8 -*-
# Generated by Django 1.10.2 on 2016-11-11 16:08
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("awards", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="awardrule",
            name="operator_name",
            field=models.CharField(
                choices=[
                    ("IS", "is"),
                    ("IS_NOT", "is not"),
                    ("GREATER", "is greater than"),
                    ("LESS", "is less than"),
                    ("IN", "in"),
                    ("NOT_IN", "not in"),
                ],
                max_length=20,
            ),
        ),
    ]
