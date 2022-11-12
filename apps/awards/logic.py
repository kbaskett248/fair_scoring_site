from apps.awards.models import Award, AwardInstance


def assign_awards(queryset, instances):
    for award in queryset.order_by("award_order", "name"):
        award.assign(instances)


class InstanceMixin:
    def assign_award(self, award: Award) -> None:
        raise NotImplementedError(
            "{0} does not implement assign".format(self.__class__.__name__)
        )

    def get_awards(self, award: Award) -> list:
        raise NotImplementedError(
            "{0} does not implement get_awards".format(self.__class__.__name__)
        )

    @classmethod
    def create_award_instance(cls, award: Award, content_object) -> AwardInstance:
        return AwardInstance.objects.create(award=award, content_object=content_object)


class InstanceBase(InstanceMixin):
    model_attr = "None"

    def __init__(self):
        self.awards = []

    def assign_award(self, award: Award):
        self.awards.append(award)
        content_object = self.get_content_object()
        if content_object:
            self.create_award_instance(award, content_object)

    def get_content_object(self):
        return getattr(self, self.model_attr, None)

    def get_awards(self):
        return self.awards

    @property
    def awards_str(self) -> str:
        return ", ".join(str(award) for award in self.get_awards())
