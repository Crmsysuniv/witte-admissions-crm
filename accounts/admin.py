from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User


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

