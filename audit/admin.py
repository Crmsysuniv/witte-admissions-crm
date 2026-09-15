from django.contrib import admin
from .models import StatusLog, Notification


@admin.register(StatusLog)
class StatusLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'application', 'old_status', 'new_status', 'changed_by', 'changed_at')
    list_filter = ('new_status', 'changed_at', 'changed_by')
    search_fields = ('application__id', 'application__applicant__username', 'application__applicant__last_name', 'comment')
    readonly_fields = ('application', 'old_status', 'new_status', 'changed_by', 'changed_at', 'comment')
    date_hierarchy = 'changed_at'


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'title', 'notification_type', 'is_read', 'created_at', 'read_at')
    list_filter = ('notification_type', 'is_read', 'created_at')
    search_fields = ('user__username', 'user__last_name', 'user__email', 'title', 'message')
    list_editable = ('is_read',)
    readonly_fields = ('created_at', 'read_at')
    date_hierarchy = 'created_at'

