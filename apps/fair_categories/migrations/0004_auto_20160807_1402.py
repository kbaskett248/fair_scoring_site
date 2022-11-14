# -*- coding: utf-8 -*-
# Generated by Django 1.9.9 on 2016-08-07 18:02
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("fair_categories", "0003_ethnicity"),
    ]

    operations = [
        migrations.AddField(
            model_name="category",
            name="active",
            field=models.BooleanField(
                default=True, help_text="Inactivate the category instead of deleting it"
            ),
        ),
        migrations.AddField(
            model_name="division",
            name="active",
            field=models.BooleanField(
                default=True, help_text="Inactivate the division instead of deleting it"
            ),
        ),
        migrations.AddField(
            model_name="ethnicity",
            name="active",
            field=models.BooleanField(
                default=True,
                help_text="Inactivate the ethnicity instead of deleting it",
            ),
        ),
        migrations.AddField(
            model_name="subcategory",
            name="active",
            field=models.BooleanField(
                default=True,
                help_text="Inactivate the subcategory instead of deleting it",
            ),
        ),
    ]