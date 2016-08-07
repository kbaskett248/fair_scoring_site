from django.contrib import admin
import django.contrib.auth.admin
# from django.contrib.auth.models import User

from .models import Judge, JudgeFairExperience, JudgeEducation


admin.site.register(JudgeFairExperience)
admin.site.register(JudgeEducation)


def get_inline_instances(self, request, obj=None):
    inline_instances = []
    if hasattr(self, 'inlines'):
        inlines = list(self.inlines)
    else:
        inlines = []

    for inline_class in self.conditional_inlines:
        if inline_class.condition(request, obj):
            inlines.append(inline_class)

    for inline_class in inlines:
        inline = inline_class(self.model, self.admin_site)
        if request:
            if not (inline.has_add_permission(request) or
                    inline.has_change_permission(request) or
                    inline.has_delete_permission(request)):
                continue
            if not inline.has_add_permission(request):
                inline.max_num = 0
        inline_instances.append(inline)
    return inline_instances


def get_formsets(self, request, obj=None):
    for inline in self.get_inline_instances(request, obj):
        yield inline.get_formset(request, obj)


def register_conditional_inline(cls, inline):
    if inline:
        cls.conditional_inlines.append(inline)


django.contrib.auth.admin.UserAdmin.conditional_inlines = []
django.contrib.auth.admin.UserAdmin.get_inline_instances = get_inline_instances
django.contrib.auth.admin.UserAdmin.get_formsets = get_formsets
django.contrib.auth.admin.UserAdmin.register_conditional_inline = classmethod(register_conditional_inline)


class JudgeInline(admin.StackedInline):
    model = Judge
    can_delete = False
    max_num = 1
    verbose_name_plural = 'Judge Information'

    @classmethod
    def condition(cls, request, obj=None):
        return obj and obj.has_perm('judges.is_judge')


django.contrib.auth.admin.UserAdmin.register_conditional_inline(JudgeInline)


# admin.site.unregister(User)
# @admin.register(User)
# class UserAdmin(UserAdmin):
#     inlines = tuple()

#     def get_inline_instances(self, request, obj=None):
#         inline_instances = []
#         inlines = list(self.inlines)

#         if obj and obj.has_perm('judges.is_judge'):
#             inlines.append(JudgeInline)

#         for inline_class in inlines:
#             inline = inline_class(self.model, self.admin_site)
#             if request:
#                 if not (inline.has_add_permission(request) or
#                         inline.has_change_permission(request) or
#                         inline.has_delete_permission(request)):
#                     continue
#                 if not inline.has_add_permission(request):
#                     inline.max_num = 0
#             inline_instances.append(inline)
#         return inline_instances

#     def get_formsets(self, request, obj=None):
#         for inline in self.get_inline_instances(request, obj):
#             yield inline.get_formset(request, obj)

# Register your models here.
