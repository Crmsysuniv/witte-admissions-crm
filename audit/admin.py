from django.contrib import admin
from django.utils.html import format_html
from .models import StatusLog, Notification, SecurityLog


@admin.register(StatusLog)
class StatusLogAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'application',
        'get_applicant',
        'get_status_transition',
        'changed_by',
        'changed_at',
        'comment',
    )
    list_filter = ('new_status', 'old_status', 'changed_at', 'changed_by')
    search_fields = (
        'application__id',
        'application__applicant__username',
        'application__applicant__last_name',
        'application__applicant__email',
        'comment',
    )
    readonly_fields = ('application', 'old_status', 'new_status', 'changed_by', 'changed_at', 'comment')
    date_hierarchy = 'changed_at'
    ordering = ('-changed_at',)

    def get_applicant(self, obj):
        return obj.application.applicant.get_full_name() or obj.application.applicant.username
    get_applicant.short_description = 'Абитуриент'

    def get_status_transition(self, obj):
        return format_html(
            '<span>{} &rarr; <strong>{}</strong></span>',
            obj.old_status or 'Новое',
            obj.new_status
        )
    get_status_transition.short_description = 'Переход статуса'


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'user',
        'title',
        'notification_type',
        'is_read',
        'created_at',
        'read_at',
    )
    list_filter = ('notification_type', 'is_read', 'created_at')
    search_fields = ('user__username', 'user__last_name', 'user__email', 'title', 'message')
    list_editable = ('is_read',)
    readonly_fields = ('created_at', 'read_at')
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)
    actions = ['mark_as_read', 'mark_as_unread']

    @admin.action(description='Отметить как прочитанные')
    def mark_as_read(self, request, queryset):
        count = queryset.update(is_read=True)
        self.message_user(request, f"Отмечено как прочитанные: {count}.")

    @admin.action(description='Отметить как непрочитанные')
    def mark_as_unread(self, request, queryset):
        count = queryset.update(is_read=False, read_at=None)
        self.message_user(request, f"Отмечено как непрочитанные: {count}.")


@admin.register(SecurityLog)
class SecurityLogAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'created_at',
        'get_event_badge',
        'get_user_display',
        'ip_address',
        'get_short_description',
    )
    list_filter = ('event_type', 'created_at', 'user__role')
    search_fields = (
        'user__username',
        'user__last_name',
        'user__email',
        'ip_address',
        'description',
        'user_agent',
    )
    readonly_fields = ('created_at', 'user', 'event_type', 'ip_address', 'user_agent', 'description')
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)

    def get_user_display(self, obj):
        if obj.user:
            return f"{obj.user.get_full_name() or obj.user.username} ({obj.user.get_role_display()})"
        return 'Анонимный гость'
    get_user_display.short_description = 'Пользователь'

    def get_short_description(self, obj):
        desc = obj.description
        return desc[:80] + '...' if len(desc) > 80 else desc
    get_short_description.short_description = 'Описание события'

    def get_event_badge(self, obj):
        colors = {
            SecurityLog.EventType.LOGIN: '#2563eb',
            SecurityLog.EventType.LOGOUT: '#64748b',
            SecurityLog.EventType.LOGIN_FAILED: '#dc2626',
            SecurityLog.EventType.ROLE_CHANGE: '#d97706',
            SecurityLog.EventType.STATUS_CHANGE: '#7c3aed',
            SecurityLog.EventType.DOCUMENT_VERIFY: '#059669',
            SecurityLog.EventType.SETTINGS_CHANGE: '#4f46e5',
            SecurityLog.EventType.EXPORT_DATA: '#0891b2',
            SecurityLog.EventType.PASSWORD_CHANGE: '#475569',
        }
        color = colors.get(obj.event_type, '#64748b')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; border-radius: 9999px; font-weight: 600; font-size: 11px;">{}</span>',
            color,
            obj.get_event_type_display()
        )
    get_event_badge.short_description = 'Тип события'
