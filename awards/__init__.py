def assign_awards(queryset, instances):
    for award in queryset.order_by('award_order', 'name'):
        award.assign(instances)


class InstanceMixin:
    def assign_award(self, award) -> None:
        raise NotImplementedError('{0} does not implement assign'.format(
            self.__class__.__name__))

    def get_awards(self, award) -> list:
        raise NotImplementedError('{0} does not implement get_awards'.format(
            self.__class__.__name__))


class InstanceBase(InstanceMixin):
    def __init__(self):
        self.awards = []

    def assign_award(self, award):
        self.awards.append(award)

    def get_awards(self):
        return self.awards

    @property
    def awards_str(self):
        return ', '.join(str(award) for award in self.get_awards())
