# -*- coding: utf-8 -*-
# Generated by Django 1.9.9 on 2016-09-13 22:49
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("rubrics", "0003_auto_20160817_1847"),
    ]

    operations = [
        migrations.AddField(
            model_name="question",
            name="required",
            field=models.BooleanField(default=True),
        ),
    ]
