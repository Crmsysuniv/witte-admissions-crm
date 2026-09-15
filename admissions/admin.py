from django.contrib import admin
from .models import Faculty, Specialty


class SpecialtyInline(admin.TabularInline):
    model = Specialty
    extra = 1
    fields = ('code', 'name', 'education_level', 'budget_places', 'paid_places', 'is_active')


@admin.register(Faculty)
class FacultyAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'specialties_count')
    search_fields = ('name', 'code')
    inlines = [SpecialtyInline]

    def specialties_count(self, obj):
        return obj.specialties.count()
    specialties_count.short_description = 'Количество направлений'


@admin.register(Specialty)
class SpecialtyAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'faculty', 'education_level', 'budget_places', 'paid_places', 'total_places', 'is_active')
    list_filter = ('faculty', 'education_level', 'is_active')
    search_fields = ('code', 'name', 'faculty__name')
    list_editable = ('budget_places', 'paid_places', 'is_active')

