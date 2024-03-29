# Generated by Django 4.1.3 on 2022-11-06 18:36

import django.core.validators
from django.db import migrations, models

import apps.judges.models


class Migration(migrations.Migration):

    dependencies = [
        ("judges", "0014_auto_20190104_2234"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="judge",
            options={
                "ordering": ("user__last_name", "user__first_name"),
                "permissions": (("is_judge", "Designates this user as a judge"),),
            },
        ),
        migrations.AlterField(
            model_name="judge",
            name="phone",
            field=apps.judges.models.PhoneField(
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
                ],
            ),
        ),
        migrations.AlterField(
            model_name="judgeeducation",
            name="id",
            field=models.BigAutoField(
                auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
            ),
        ),
        migrations.AlterField(
            model_name="judgefairexperience",
            name="id",
            field=models.BigAutoField(
                auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
            ),
        ),
    ]
