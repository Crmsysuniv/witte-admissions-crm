from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from .models import User, ApplicantProfile, OfficerProfile


class ApplicantProfileInline(admin.StackedInline):
    model = ApplicantProfile
    can_delete = False
    verbose_name = 'Профиль абитуриента'
    verbose_name_plural = 'Профиль абитуриента'
    fk_name = 'user'
    extra = 0
    fields = ('birth_date', 'snils', ('passport_series', 'passport_number'), 'passport_issued_by', 'passport_issue_date', 'address')


class OfficerProfileInline(admin.StackedInline):
    model = OfficerProfile
    can_delete = False
    verbose_name = 'Профиль сотрудника'
    verbose_name_plural = 'Профиль сотрудника'
    fk_name = 'user'
    extra = 0
    fields = ('position', 'cabinet')


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    model = User
    list_display = (
        'id',
        'username',
        'email',
        'get_full_name_display',
        'get_role_badge',
        'phone',
        'is_staff',
        'is_active',
        'date_joined',
    )
    list_filter = ('role', 'is_staff', 'is_superuser', 'is_active', 'date_joined')
    search_fields = ('username', 'email', 'first_name', 'last_name', 'phone', 'applicant_profile__snils')
    ordering = ('-date_joined',)
    inlines = [ApplicantProfileInline, OfficerProfileInline]
    actions = ['make_officer', 'make_applicant', 'activate_users', 'deactivate_users']

    fieldsets = UserAdmin.fieldsets + (
        ('Роль и контакты в CRM', {'fields': ('role', 'phone')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Роль и контакты в CRM', {'fields': ('role', 'phone')}),
    )

    def get_full_name_display(self, obj):
        return obj.get_full_name() or '—'
    get_full_name_display.short_description = 'ФИО пользователя'
    get_full_name_display.admin_order_field = 'last_name'

    def get_role_badge(self, obj):
        colors = {
            User.Role.ADMIN: '#dc2626',
            User.Role.OFFICER: '#2563eb',
            User.Role.APPLICANT: '#059669',
        }
        color = colors.get(obj.role, '#64748b')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; border-radius: 9999px; font-weight: bold; font-size: 11px;">{}</span>',
            color,
            obj.get_role_display()
        )
    get_role_badge.short_description = 'Роль в CRM'
    get_role_badge.admin_order_field = 'role'

    @admin.action(description='Назначить роль «Сотрудник приемной комиссии»')
    def make_officer(self, request, queryset):
        count = queryset.update(role=User.Role.OFFICER, is_staff=True)
        for u in queryset:
            OfficerProfile.objects.get_or_create(user=u)
        self.message_user(request, f"Выбранным пользователям ({count}) назначена роль сотрудника приемной комиссии.")

    @admin.action(description='Снять служебные права (назначить роль «Абитуриент»)')
    def make_applicant(self, request, queryset):
        count = queryset.filter(is_superuser=False).update(role=User.Role.APPLICANT, is_staff=False)
        self.message_user(request, f"Выбранным пользователям ({count}) назначена роль абитуриента.")

    @admin.action(description='Активировать выбранные учетные записи')
    def activate_users(self, request, queryset):
        count = queryset.update(is_active=True)
        self.message_user(request, f"Успешно активировано учетных записей: {count}.")

    @admin.action(description='Заблокировать выбранные учетные записи')
    def deactivate_users(self, request, queryset):
        count = queryset.exclude(id=request.user.id).update(is_active=False)
        self.message_user(request, f"Успешно заблокировано учетных записей: {count}.")


@admin.register(ApplicantProfile)
class ApplicantProfileAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'get_full_name', 'snils', 'passport_series', 'passport_number', 'birth_date')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'user__email', 'snils', 'passport_series', 'passport_number')
    list_filter = ('birth_date',)
    ordering = ('user__last_name', 'user__first_name')

    def get_full_name(self, obj):
        return obj.user.get_full_name() or obj.user.username
    get_full_name.short_description = 'ФИО абитуриента'


@admin.register(OfficerProfile)
class OfficerProfileAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'get_full_name', 'position', 'cabinet')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'position', 'cabinet')
    list_filter = ('position',)

    def get_full_name(self, obj):
        return obj.user.get_full_name() or obj.user.username
    get_full_name.short_description = 'ФИО сотрудника'
