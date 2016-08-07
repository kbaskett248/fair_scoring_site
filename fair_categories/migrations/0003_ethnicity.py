# -*- coding: utf-8 -*-
# Generated by Django 1.9.4 on 2016-03-22 01:17
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('fair_categories', '0002_subcategory_abbreviation'),
    ]

    operations = [
        migrations.CreateModel(
            name='Ethnicity',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('short_description', models.CharField(max_length=50, verbose_name='Ethnicity name')),
            ],
        ),
    ]