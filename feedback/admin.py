from django.contrib import admin
from django.utils import timezone
from .models import FeedbackMessage


@admin.register(FeedbackMessage)
class FeedbackMessageAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'full_name',
        'phone',
        'email',
        'subject',
        'status',
        'responded_by',
        'created_at',
    )
    list_filter = ('status', 'created_at', 'responded_at')
    search_fields = ('full_name', 'phone', 'email', 'subject', 'message', 'officer_response')
    list_editable = ('status',)
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at', 'updated_at', 'responded_at')
    fieldsets = (
        ('Информация об обращении', {
            'fields': ('full_name', 'phone', 'email', 'subject', 'message', 'created_at')
        }),
        ('Обработка обращения', {
            'fields': ('status', 'officer_response', 'responded_by', 'responded_at', 'updated_at')
        }),
    )

    def save_model(self, request, obj, form, change):
        if obj.officer_response and not obj.responded_at:
            obj.responded_at = timezone.now()
            if not obj.responded_by:
                obj.responded_by = request.user
            if obj.status == FeedbackMessage.Status.NEW:
                obj.status = FeedbackMessage.Status.RESOLVED
        super().save_model(request, obj, form, change)

