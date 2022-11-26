from django.db import models


class FeedbackForm(models.Model):
    rubric = models.ForeignKey("Rubric", on_delete=models.CASCADE)

    def __str__(self):
        return f"Feedback Form for {self.rubric.name}"
