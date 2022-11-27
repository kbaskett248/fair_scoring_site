# Generated by Django 4.1.3 on 2022-11-26 16:58

from django.db import migrations

import apps.rubrics.models.feedback_form


class Migration(migrations.Migration):

    dependencies = [
        ("rubrics", "0010_alter_feedbackmodule_module_type_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="markdownfeedbackmodule",
            name="content",
            field=apps.rubrics.models.feedback_form.MarkdownField(
                default="# Heading 1\n\nWrite content here",
                help_text="You may include <code>{{ average_score }}</code> in the text. It will be replaced by the average score for the project.",
                validators=[
                    apps.rubrics.models.feedback_form.MarkdownField.validate_markdown
                ],
            ),
        ),
    ]