from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, ApplicantProfile, OfficerProfile


class ApplicantProfileInline(admin.StackedInline):
    model = ApplicantProfile
    can_delete = False
    verbose_name = 'Профиль абитуриента'
    verbose_name_plural = 'Профиль абитуриента'
    fk_name = 'user'
    extra = 0


class OfficerProfileInline(admin.StackedInline):
    model = OfficerProfile
    can_delete = False
    verbose_name = 'Профиль сотрудника'
    verbose_name_plural = 'Профиль сотрудника'
    fk_name = 'user'
    extra = 0


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    model = User
    list_display = (
        'username',
        'email',
        'first_name',
        'last_name',
        'role',
        'phone',
        'is_staff',
        'is_active',
    )
    list_filter = ('role', 'is_staff', 'is_superuser', 'is_active')
    fieldsets = UserAdmin.fieldsets + (
        ('Дополнительная информация', {'fields': ('role', 'phone')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Дополнительная информация', {'fields': ('role', 'phone')}),
    )
    search_fields = ('username', 'email', 'first_name', 'last_name', 'phone')
    inlines = [ApplicantProfileInline, OfficerProfileInline]


@admin.register(ApplicantProfile)
class ApplicantProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'birth_date', 'snils', 'passport_series', 'passport_number')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'snils', 'passport_number', 'passport_series')
    list_filter = ('birth_date',)


@admin.register(OfficerProfile)
class OfficerProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'position', 'cabinet')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'position', 'cabinet')
    list_filter = ('position',)


