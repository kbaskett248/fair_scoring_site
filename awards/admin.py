from django import forms
from django.contrib import admin

from awards.models import Award, AwardRule, AwardInstance


def capitalize_first(string):
    return string[0].upper() + string[1:]


def build_trait_list(traits):
    trait_list = []
    insert_none = True
    for t in traits:
        try:
            internal, external = t
        except ValueError:
            internal, external = t, capitalize_first(t)
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


class AwardAdmin(admin.ModelAdmin):
    model = Award
    inlines = (AwardRuleInline, AwardInstanceInline)
    list_display = ('name', 'award_order', 'num_awards_str')
    ordering = ('award_order', 'name')

