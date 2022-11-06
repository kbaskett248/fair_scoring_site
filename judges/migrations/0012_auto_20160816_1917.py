# -*- coding: utf-8 -*-
# Generated by Django 1.9.9 on 2016-08-16 23:17
from __future__ import unicode_literals

import django.core.validators
from django.db import migrations, models

import judges.models


class Migration(migrations.Migration):

    dependencies = [
        ("fair_categories", "0004_auto_20160807_1402"),
        ("judges", "0011_auto_20160813_2316"),
    ]

    operations = [
        migrations.AddField(
            model_name="judge",
            name="categories",
            field=models.ManyToManyField(to="fair_categories.Category"),
        ),
        migrations.AddField(
            model_name="judge",
            name="divisions",
            field=models.ManyToManyField(to="fair_categories.Division"),
        ),
        migrations.AlterField(
            model_name="judge",
            name="phone",
            field=judges.models.PhoneField(
                max_length=15,
                validators=[
                    django.core.validators.RegexValidator(
                        message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed.",
                        regex="^\\+?1?\\d{9,15}$",
                    ),
                    django.core.validators.RegexValidator(
                        message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed.",
                        regex="^\\+?1?\\d{9,15}$",
                    ),
                    django.core.validators.RegexValidator(
                        message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed.",
                        regex="^\\+?1?\\d{9,15}$",
                    ),
                ],
            ),
        ),
    ]
