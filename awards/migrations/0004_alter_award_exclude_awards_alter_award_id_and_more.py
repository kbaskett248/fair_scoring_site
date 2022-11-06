# Generated by Django 4.1.3 on 2022-11-06 18:36

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("awards", "0003_auto_20161212_2107"),
    ]

    operations = [
        migrations.AlterField(
            model_name="award",
            name="exclude_awards",
            field=models.ManyToManyField(blank=True, to="awards.award"),
        ),
        migrations.AlterField(
            model_name="award",
            name="id",
            field=models.BigAutoField(
                auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
            ),
        ),
        migrations.AlterField(
            model_name="awardinstance",
            name="id",
            field=models.BigAutoField(
                auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
            ),
        ),
        migrations.AlterField(
            model_name="awardrule",
            name="id",
            field=models.BigAutoField(
                auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
            ),
        ),
    ]