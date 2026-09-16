from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html
from .models import FeedbackMessage


@admin.register(FeedbackMessage)
class FeedbackMessageAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'full_name',
        'phone',
        'email',
        'subject',
        'get_status_badge',
        'responded_by',
        'created_at',
        'responded_at',
    )
    list_filter = ('status', 'created_at', 'responded_at', 'responded_by')
    search_fields = ('full_name', 'phone', 'email', 'subject', 'message', 'officer_response')
    list_editable = ()
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at', 'updated_at', 'responded_at')
    ordering = ('-created_at',)
    actions = ['mark_in_progress', 'mark_resolved', 'mark_closed']

    fieldsets = (
        ('Информация об обращении', {
            'fields': ('full_name', 'phone', 'email', 'subject', 'message', 'created_at')
        }),
        ('Обработка обращения', {
            'fields': ('status', 'officer_response', 'responded_by', 'responded_at', 'updated_at')
        }),
    )

    def get_status_badge(self, obj):
        colors = {
            FeedbackMessage.Status.NEW: ('#dc2626', '#fee2e2'),
            FeedbackMessage.Status.IN_PROGRESS: ('#d97706', '#fef3c7'),
            FeedbackMessage.Status.RESOLVED: ('#059669', '#d1fae5'),
            FeedbackMessage.Status.CLOSED: ('#475569', '#f1f5f9'),
        }
        fg, bg = colors.get(obj.status, ('#334155', '#e2e8f0'))
        return format_html(
            '<span style="background-color: {}; color: {}; padding: 3px 8px; border-radius: 6px; font-weight: 600; font-size: 11px;">{}</span>',
            bg, fg, obj.get_status_display()
        )
    get_status_badge.short_description = 'Статус'
    get_status_badge.admin_order_field = 'status'

    def save_model(self, request, obj, form, change):
        if obj.officer_response and not obj.responded_at:
            obj.responded_at = timezone.now()
            if not obj.responded_by:
                obj.responded_by = request.user
            if obj.status == FeedbackMessage.Status.NEW:
                obj.status = FeedbackMessage.Status.RESOLVED
        super().save_model(request, obj, form, change)

    @admin.action(description='Взять обращения в обработку (В работе)')
    def mark_in_progress(self, request, queryset):
        count = queryset.update(status=FeedbackMessage.Status.IN_PROGRESS)
        self.message_user(request, f"Переведено в статус «В работе»: {count} обращений.")

    @admin.action(description='Отметить как обработанные (Решено)')
    def mark_resolved(self, request, queryset):
        now = timezone.now()
        count = queryset.update(status=FeedbackMessage.Status.RESOLVED, responded_at=now, responded_by=request.user)
        self.message_user(request, f"Отмечено как решенные: {count} обращений.")

    @admin.action(description='Закрыть выбранные обращения (В архив)')
    def mark_closed(self, request, queryset):
        count = queryset.update(status=FeedbackMessage.Status.CLOSED)
        self.message_user(request, f"Закрыто обращений: {count}.")
