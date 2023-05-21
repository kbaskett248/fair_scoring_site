import django.contrib.auth.admin
from django.contrib import admin

from .models import Judge, JudgeEducation, JudgeFairExperience

admin.site.register(JudgeFairExperience)
admin.site.register(JudgeEducation)


# Provide the ability to register and display conditional inlines.
def get_inline_instances(self, request, obj=None):
    inline_instances = []
    inlines = list(self.inlines) if hasattr(self, "inlines") else []

    for inline_class in self.conditional_inlines:
        if inline_class.condition(request, obj):
            inlines.append(inline_class)

    for inline_class in inlines:
        inline = inline_class(self.model, self.admin_site)
        if request:
            if not (
                inline.has_add_permission(request, obj)
                or inline.has_change_permission(request, obj)
                or inline.has_delete_permission(request, obj)
            ):
                continue
            if not inline.has_add_permission(request, obj):
                inline.max_num = 0
        inline_instances.append(inline)
    return inline_instances


def get_formsets(self, request, obj=None):
    for inline in self.get_inline_instances(request, obj):
        yield inline.get_formset(request, obj)


def register_conditional_inline(cls, inline):
    if inline:
        cls.conditional_inlines.append(inline)


# Monkeypatch UserAdmin to add support for conditional inlines.
django.contrib.auth.admin.UserAdmin.conditional_inlines = []
django.contrib.auth.admin.UserAdmin.get_inline_instances = get_inline_instances
django.contrib.auth.admin.UserAdmin.get_formsets = get_formsets
django.contrib.auth.admin.UserAdmin.register_conditional_inline = classmethod(
    register_conditional_inline
)


# Add JudgeInline as a conditional inline
class JudgeInline(admin.StackedInline):
    model = Judge
    can_delete = False
    max_num = 1
    verbose_name_plural = "Judge Information"

    @classmethod
    def condition(cls, request, obj=None):
        return obj and obj.has_perm("judges.is_judge")


django.contrib.auth.admin.UserAdmin.register_conditional_inline(JudgeInline)
