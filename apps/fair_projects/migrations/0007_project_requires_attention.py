# Generated by Django 2.1.3 on 2018-12-07 01:33

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("fair_projects", "0006_auto_20161109_2113"),
    ]

    operations = [
        migrations.AddField(
            model_name="project",
            name="requires_attention",
            field=models.BooleanField(default=False),
        ),
    ]