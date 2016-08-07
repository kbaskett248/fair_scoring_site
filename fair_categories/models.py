from django.db import models


# Create your models here.
class Division(models.Model):
    active = models.BooleanField(
        help_text=('Inactivate the division instead of deleting it'),
        default=True
    )
    short_description = models.CharField(
        max_length=100,
        verbose_name='Division name'
    )

    def __str__(self):
        return self.short_description


class Category(models.Model):
    active = models.BooleanField(
        help_text=('Inactivate the category instead of deleting it'),
        default=True
    )
    short_description = models.CharField(
        max_length=100,
        verbose_name='Category name'
    )

    def __str__(self):
        return self.short_description


class Subcategory(models.Model):
    active = models.BooleanField(
        help_text=('Inactivate the subcategory instead of deleting it'),
        default=True
    )
    abbreviation = models.CharField(
        max_length=10,
        verbose_name='Abbreviation'
    )
    short_description = models.CharField(
        max_length=100,
        verbose_name='Subcategory name'
    )
    category = models.ForeignKey(Category, on_delete=models.CASCADE)

    def __str__(self):
        return self.short_description


class Ethnicity(models.Model):
    active = models.BooleanField(
        help_text=('Inactivate the ethnicity instead of deleting it'),
        default=True
    )
    short_description = models.CharField(
        max_length=50,
        verbose_name='Ethnicity name')

    def __str__(self):
        return self.short_description
