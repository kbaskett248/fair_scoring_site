# Generated by Django 2.1.5 on 2019-01-19 17:59

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('fair_projects', '0008_project_judge_notes'),
    ]

    operations = [
        migrations.AddField(
            model_name='judginginstance',
            name='locked',
            field=models.BooleanField(default=False),
        ),
    ]