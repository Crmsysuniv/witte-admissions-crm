from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Sum
from .models import (
    Faculty,
    Specialty,
    EducationProgram,
    ExamSubject,
    Application,
    ApplicationDocument,
    ExamScore,
    CampaignSettings,
)
from audit.models import StatusLog, Notification


class ApplicationDocumentInline(admin.TabularInline):
    model = ApplicationDocument
    extra = 0
    fields = ('document_type', 'file', 'is_verified', 'comment', 'uploaded_at')
    readonly_fields = ('uploaded_at',)


class ExamScoreInline(admin.TabularInline):
    model = ExamScore
    extra = 0
    fields = ('subject', 'score', 'exam_type', 'year', 'document_number', 'is_verified')


class EducationProgramInline(admin.TabularInline):
    model = EducationProgram
    extra = 0
    fields = ('study_form', 'tuition_fee', 'duration', 'is_active')


class SpecialtyInline(admin.TabularInline):
    model = Specialty
    extra = 0
    fields = ('code', 'name', 'education_level', 'budget_places', 'paid_places', 'is_active')


class StatusLogInline(admin.TabularInline):
    model = StatusLog
    extra = 0
    can_delete = False
    readonly_fields = ('old_status', 'new_status', 'changed_by', 'changed_at', 'comment')


@admin.register(Faculty)
class FacultyAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'code', 'get_specialties_count', 'get_budget_places', 'get_paid_places')
    search_fields = ('name', 'code', 'description')
    inlines = [SpecialtyInline]

    def get_specialties_count(self, obj):
        return obj.specialties.count()
    get_specialties_count.short_description = 'Направлений'

    def get_budget_places(self, obj):
        return obj.specialties.aggregate(Sum('budget_places'))['budget_places__sum'] or 0
    get_budget_places.short_description = 'Бюджетных мест'

    def get_paid_places(self, obj):
        return obj.specialties.aggregate(Sum('paid_places'))['paid_places__sum'] or 0
    get_paid_places.short_description = 'Платных мест'


@admin.register(Specialty)
class SpecialtyAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'code',
        'name',
        'faculty',
        'education_level',
        'budget_places',
        'paid_places',
        'total_places',
        'is_active',
    )
    list_filter = ('faculty', 'education_level', 'is_active')
    search_fields = ('code', 'name', 'faculty__name')
    list_editable = ('budget_places', 'paid_places', 'is_active')
    ordering = ('faculty', 'code')
    inlines = [EducationProgramInline]
    actions = ['activate_specialties', 'deactivate_specialties']

    @admin.action(description='Активировать прием на выбранные направления')
    def activate_specialties(self, request, queryset):
        count = queryset.update(is_active=True)
        self.message_user(request, f"Активирован прием для {count} направлений.")

    @admin.action(description='Приостановить прием на выбранные направления')
    def deactivate_specialties(self, request, queryset):
        count = queryset.update(is_active=False)
        self.message_user(request, f"Приостановлен прием для {count} направлений.")


@admin.register(EducationProgram)
class EducationProgramAdmin(admin.ModelAdmin):
    list_display = ('id', 'specialty', 'study_form', 'tuition_fee', 'duration', 'is_active')
    list_filter = ('study_form', 'is_active', 'specialty__faculty', 'specialty__education_level')
    search_fields = ('specialty__name', 'specialty__code', 'duration')
    list_editable = ('tuition_fee', 'is_active')
    ordering = ('specialty', 'study_form')
    actions = ['activate_programs', 'deactivate_programs']

    @admin.action(description='Активировать выбранные программы')
    def activate_programs(self, request, queryset):
        count = queryset.update(is_active=True)
        self.message_user(request, f"Активировано программ: {count}.")

    @admin.action(description='Деактивировать выбранные программы')
    def deactivate_programs(self, request, queryset):
        count = queryset.update(is_active=False)
        self.message_user(request, f"Деактивировано программ: {count}.")


@admin.register(ExamSubject)
class ExamSubjectAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'min_score', 'description')
    search_fields = ('name', 'description')
    list_editable = ('min_score',)
    ordering = ('name',)


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'get_applicant_name',
        'get_specialty_display',
        'get_study_form',
        'financing_type',
        'get_total_score',
        'get_status_badge',
        'submission_date',
        'updated_at',
    )
    list_filter = (
        'status',
        'financing_type',
        'program__study_form',
        'program__specialty__faculty',
        'program__specialty__education_level',
        'submission_date',
    )
    search_fields = (
        'id',
        'applicant__username',
        'applicant__first_name',
        'applicant__last_name',
        'applicant__email',
        'applicant__applicant_profile__snils',
        'program__specialty__name',
        'program__specialty__code',
    )
    list_editable = ('financing_type',)
    date_hierarchy = 'submission_date'
    ordering = ('-submission_date',)
    inlines = [ApplicationDocumentInline, ExamScoreInline, StatusLogInline]
    actions = [
        'action_approve_applications',
        'action_require_documents',
        'action_reject_applications',
        'action_enroll_applications',
    ]

    def get_applicant_name(self, obj):
        return obj.applicant.get_full_name() or obj.applicant.username
    get_applicant_name.short_description = 'Абитуриент'
    get_applicant_name.admin_order_field = 'applicant__last_name'

    def get_specialty_display(self, obj):
        return f"{obj.program.specialty.code} {obj.program.specialty.name}"
    get_specialty_display.short_description = 'Направление'

    def get_study_form(self, obj):
        return obj.program.get_study_form_display()
    get_study_form.short_description = 'Форма'

    def get_total_score(self, obj):
        score = obj.total_score
        return f"{score} б." if score else "0 б."
    get_total_score.short_description = 'Сумма баллов'

    def get_status_badge(self, obj):
        badge_styles = {
            Application.Status.DRAFT: ('#64748b', '#f1f5f9'),
            Application.Status.SUBMITTED: ('#1d4ed8', '#dbeafe'),
            Application.Status.UNDER_REVIEW: ('#d97706', '#fef3c7'),
            Application.Status.DOCUMENTS_REQUIRED: ('#c2410c', '#ffedd5'),
            Application.Status.APPROVED: ('#047857', '#d1fae5'),
            Application.Status.ENROLLED: ('#6d28d9', '#ede9fe'),
            Application.Status.REJECTED: ('#b91c1c', '#fee2e2'),
            Application.Status.WITHDRAWN: ('#475569', '#f1f5f9'),
        }
        fg, bg = badge_styles.get(obj.status, ('#334155', '#e2e8f0'))
        return format_html(
            '<span style="background-color: {}; color: {}; padding: 3px 8px; border-radius: 6px; font-weight: 600; font-size: 11px;">{}</span>',
            bg, fg, obj.get_status_display()
        )
    get_status_badge.short_description = 'Статус'
    get_status_badge.admin_order_field = 'status'

    def save_model(self, request, obj, form, change):
        if change and 'status' in form.changed_data:
            old_status = form.initial.get('status', '')
            StatusLog.objects.create(
                application=obj,
                old_status=old_status,
                new_status=obj.status,
                changed_by=request.user,
                comment="Статус изменен через панель администратора Django"
            )
            # Уведомление
            Notification.objects.create(
                user=obj.applicant,
                application=obj,
                title=f"Изменение статуса заявления №{obj.id}",
                message=f"Статус вашего заявления на направление «{obj.program.specialty.name}» изменен на «{obj.get_status_display()}».",
                notification_type=Notification.NotificationType.STATUS_CHANGE
            )
        super().save_model(request, obj, form, change)

    @admin.action(description='Одобрить выбранные заявления (допустить к конкурсу)')
    def action_approve_applications(self, request, queryset):
        count = 0
        for app in queryset:
            old_status = app.status
            app.status = Application.Status.APPROVED
            app.save()
            StatusLog.objects.create(
                application=app,
                old_status=old_status,
                new_status=app.status,
                changed_by=request.user,
                comment="Массовое одобрение через панель администратора"
            )
            count += 1
        self.message_user(request, f"Успешно одобрено заявлений: {count}.")

    @admin.action(description='Запросить недостающие документы')
    def action_require_documents(self, request, queryset):
        count = 0
        for app in queryset:
            old_status = app.status
            app.status = Application.Status.DOCUMENTS_REQUIRED
            app.save()
            StatusLog.objects.create(
                application=app,
                old_status=old_status,
                new_status=app.status,
                changed_by=request.user,
                comment="Запрос исправлений/документов через админку"
            )
            count += 1
        self.message_user(request, f"Переведено в статус «Требуются документы»: {count}.")

    @admin.action(description='Отклонить выбранные заявления')
    def action_reject_applications(self, request, queryset):
        count = 0
        for app in queryset:
            old_status = app.status
            app.status = Application.Status.REJECTED
            app.save()
            StatusLog.objects.create(
                application=app,
                old_status=old_status,
                new_status=app.status,
                changed_by=request.user,
                comment="Отклонено через панель администратора"
            )
            count += 1
        self.message_user(request, f"Отклонено заявлений: {count}.")

    @admin.action(description='Зачислить выбранных абитуриентов (приказ)')
    def action_enroll_applications(self, request, queryset):
        count = 0
        for app in queryset:
            old_status = app.status
            app.status = Application.Status.ENROLLED
            app.save()
            StatusLog.objects.create(
                application=app,
                old_status=old_status,
                new_status=app.status,
                changed_by=request.user,
                comment="Зачисление в состав студентов через приказ в админке"
            )
            count += 1
        self.message_user(request, f"Зачислено абитуриентов: {count}.")


@admin.register(ApplicationDocument)
class ApplicationDocumentAdmin(admin.ModelAdmin):
    list_display = ('id', 'application', 'get_applicant', 'document_type', 'file', 'is_verified', 'uploaded_at')
    list_filter = ('document_type', 'is_verified', 'uploaded_at')
    search_fields = ('application__id', 'application__applicant__username', 'application__applicant__last_name', 'comment')
    list_editable = ('is_verified',)
    ordering = ('-uploaded_at',)
    actions = ['verify_documents', 'unverify_documents']

    def get_applicant(self, obj):
        return obj.application.applicant.get_full_name() or obj.application.applicant.username
    get_applicant.short_description = 'Абитуриент'

    @admin.action(description='Подтвердить верификацию выбранных документов')
    def verify_documents(self, request, queryset):
        count = queryset.update(is_verified=True)
        self.message_user(request, f"Верифицировано документов: {count}.")

    @admin.action(description='Снять отметку верификации с выбранных документов')
    def unverify_documents(self, request, queryset):
        count = queryset.update(is_verified=False)
        self.message_user(request, f"Снята верификация с документов: {count}.")


@admin.register(ExamScore)
class ExamScoreAdmin(admin.ModelAdmin):
    list_display = ('id', 'application', 'get_applicant', 'subject', 'score', 'is_passing_score', 'exam_type', 'year', 'is_verified')
    list_filter = ('exam_type', 'is_verified', 'subject', 'year')
    search_fields = ('application__id', 'application__applicant__username', 'application__applicant__last_name', 'subject__name', 'document_number')
    list_editable = ('score', 'is_verified')
    ordering = ('application', 'subject')
    actions = ['verify_scores']

    def get_applicant(self, obj):
        return obj.application.applicant.get_full_name() or obj.application.applicant.username
    get_applicant.short_description = 'Абитуриент'

    def is_passing_score(self, obj):
        return obj.is_passing
    is_passing_score.boolean = True
    is_passing_score.short_description = 'Порог пройден'

    @admin.action(description='Подтвердить баллы выбранных испытаний')
    def verify_scores(self, request, queryset):
        count = queryset.update(is_verified=True)
        self.message_user(request, f"Подтверждены баллы для {count} записей.")


@admin.register(CampaignSettings)
class CampaignSettingsAdmin(admin.ModelAdmin):
    list_display = (
        'campaign_name',
        'is_active',
        'start_date',
        'end_date_budget_ege',
        'end_date_paid',
        'max_applications_per_applicant',
        'max_file_size_mb',
        'show_announcement',
        'updated_at',
    )
    fieldsets = (
        ('Статус кампании', {
            'fields': ('campaign_name', 'is_active', 'allow_document_updates', 'auto_notify_status_change')
        }),
        ('Календарный регламент', {
            'fields': ('start_date', 'end_date_budget_vi', 'end_date_budget_ege', 'end_date_paid')
        }),
        ('Лимиты системы', {
            'fields': ('max_applications_per_applicant', 'max_file_size_mb')
        }),
        ('Системное объявление', {
            'fields': ('show_announcement', 'announcement_type', 'system_announcement')
        }),
        ('Контакты комиссии', {
            'fields': ('hotline_phone', 'support_email')
        }),
    )
