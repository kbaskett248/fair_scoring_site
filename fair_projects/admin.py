from django.contrib import admin
import django.contrib.auth.admin

from .models import School, Teacher, Student, Project


class StudentInline(admin.StackedInline):
    model = Student


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    model = Project
    list_display = ('number', 'title', 'category', 'division')
    list_filter = ('category', 'division')
    inlines = (StudentInline, )


class TeacherInline(admin.StackedInline):
    model = Teacher
    can_delete = False
    max_num = 1
    verbose_name_plural = 'Teacher Information'

    @classmethod
    def condition(cls, request, obj=None):
        return obj and obj.has_perm('fair_projects.is_teacher')


django.contrib.auth.admin.UserAdmin.register_conditional_inline(TeacherInline)

# Register your models here.
admin.site.register(School)