from django.contrib import admin


from .models import Division, Category, Subcategory, Ethnicity


class SubcategoryInline(admin.TabularInline):
    model = Subcategory
    verbose_name_plural = "Subcategories"


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    model = Category
    inlines = (SubcategoryInline,)
    verbose_name_plural = "Categories"


# Register your models here.
admin.site.register(Division)
admin.site.register(Ethnicity)
