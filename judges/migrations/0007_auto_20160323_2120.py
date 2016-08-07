# -*- coding: utf-8 -*-
# Generated by Django 1.9.4 on 2016-03-24 01:20
from __future__ import unicode_literals

import django.core.validators
from django.db import migrations
import judges.models


class Migration(migrations.Migration):

    dependencies = [
        ('judges', '0006_auto_20160321_2224'),
    ]

    operations = [
        migrations.AlterField(
            model_name='judge',
            name='phone',
            field=judges.models.PhoneField(max_length=15, validators=[django.core.validators.RegexValidator(message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed.", regex='^\\+?1?\\d{9,15}$'), django.core.validators.RegexValidator(message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed.", regex='^\\+?1?\\d{9,15}$'), django.core.validators.RegexValidator(message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed.", regex='^\\+?1?\\d{9,15}$')]),
        ),
    ]
