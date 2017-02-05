from django import forms
from django.contrib import admin
from django.core.exceptions import FieldError, ValidationError
from django.utils.translation import gettext as _

from awards.models import Award, AwardRule, AwardInstance


def format_external_name(string: str):
    return string.replace("_", " ").title()


def build_trait_list(traits):
    trait_list = []
    insert_none = True
    for t in traits:
        try:
            internal, external = t
        except ValueError:
            internal, external = t, format_external_name(t)
        finally:
            if internal is None:
                insert_none = False
            trait_list.append((internal, external))
    trait_list.sort()
    if insert_none:
        trait_list.insert(0, (None, '---------'))
    return trait_list


class AwardRuleForm(forms.ModelForm):
    class Meta:
        model = AwardRule
        fields = ('trait', 'operator_name', 'value')

    traits = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        choices = self.__class__.get_possible_traits()
        if choices:
            self.fields['trait'] = forms.ChoiceField(choices=choices)

    @classmethod
    def get_possible_traits(cls):
        if cls.traits:
            return build_trait_list(cls.traits)
        else:
            return None

    @staticmethod
    def get_validator_name(trait: str) -> str:
        return 'validate_' + trait

    def clean(self):
        cleaned_data = super(AwardRuleForm, self).clean()

        operator_name = cleaned_data.get('operator_name', None)
        if operator_name == 'IN' or operator_name == 'NOT_IN':
            cleaned_data['value'] = ','.join(
                item.strip() for item in self.individual_value_iterator(**cleaned_data)
                if item.strip())

        trait = cleaned_data.get('trait', None)
        if trait is not None:
            validator_name = self.get_validator_name(trait)
            if hasattr(self, validator_name):
                getattr(self, validator_name)(**cleaned_data)

        return cleaned_data

    def individual_value_iterator(self, operator_name=None, value=None, **additional_fields):
        if (operator_name == 'IN' or operator_name == 'NOT_IN') and value is not None:
            for item in value.split(','):
                yield item
        else:
            yield value

    @staticmethod
    def raise_default_validation_error(params):
        raise ValidationError('%(value)s is not a valid value for the %(trait)s trait',
                              code='invalid trait value',
                              params=params)


class AwardRuleInline(admin.TabularInline):
    model = AwardRule
    form = AwardRuleForm
    can_delete = True
    verbose_name = 'Rule'
    verbose_name_plural = 'Rules'


class AwardInstanceInline(admin.TabularInline):
    model = AwardInstance
    can_delete = True
    exclude = ('content_type', 'object_id')
    readonly_fields = ('content_object_str', )

    def has_add_permission(self, request):
        return False


@admin.register(Award)
class AwardAdmin(admin.ModelAdmin):
    model = Award
    inlines = (AwardRuleInline, AwardInstanceInline)
    list_display = ('name', 'award_order', 'num_awards_str')
    ordering = ('award_order', 'name')
    list_filter = ('awardrule__trait', )


@admin.register(AwardInstance)
class AwardInstanceAdmin(admin.ModelAdmin):
    model = AwardInstance
    fields = ('award', 'content_object')
    readonly_fields = ('award', 'content_object')
    list_display = ('award', 'content_object')
    ordering = ('award', )
    list_filter = ('award', 'award__awardrule__trait')

    def has_add_permission(self, request):
        return False


class TraitListFilter(admin.SimpleListFilter):
    # Human-readable title which will be displayed in the
    # right admin sidebar just above the filter options.
    title = _('rule trait')

    # Parameter for the filter that will be used in the URL query.
    parameter_name = 'trait'

    award_rule_form_class = AwardRuleForm

    def lookups(self, request, model_admin):
        """
        Returns a list of tuples. The first element in each
        tuple is the coded value for the option that will
        appear in the URL query. The second element is the
        human-readable name for the option that will appear
        in the right sidebar.
        """
        traits = self.award_rule_form_class.get_possible_traits()
        if traits:
            return filter(lambda x: x[0] is not None, traits)
        else:
            return []

    def queryset(self, request, queryset):
        """
        Returns the filtered queryset based on the value
        provided in the query string and retrievable via
        `self.value()`.
        """
        # Compare the requested value (either '80s' or '90s')
        # to decide how to filter the queryset.
        if self.value():
            try:
                return queryset.filter(award__awardrule__trait=self.value())
            except FieldError:
                return queryset.filter(awardrule__trait=self.value())
