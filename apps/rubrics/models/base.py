from django.db import models


class ValidatedModel(models.Model):
    """Adds additional validation to a model on save.

    This class defines a framework for adding additional validation
    on save of an object. The validation is written in such a way that it
    can easily be re-used by forms. As such, the validation functions expect
    dictionaries.
    """

    class Meta:
        abstract = True

    def save(self, **kwargs):
        data = self.get_field_dict()
        self.validate(**data)
        self.validate_instance(**data)

        super(ValidatedModel, self).save(**kwargs)

    def get_field_dict(self) -> dict:
        data = {}
        for field in self._meta.fields:
            data[field.name] = getattr(self, field.name)
        return data

    def validate_instance(self, **fields):
        pass

    @classmethod
    def validate(cls, **fields):
        pass
