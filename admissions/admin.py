from django.contrib import admin
from .models import (
    Faculty,
    Specialty,
    EducationProgram,
    ExamSubject,
    Application,
    ApplicationDocument,
    ExamScore,
)


class ApplicationDocumentInline(admin.TabularInline):
    model = ApplicationDocument
    extra = 1
    fields = ('document_type', 'file', 'is_verified', 'comment', 'uploaded_at')
    readonly_fields = ('uploaded_at',)


class ExamScoreInline(admin.TabularInline):
    model = ExamScore
    extra = 1
    fields = ('subject', 'score', 'exam_type', 'year', 'document_number', 'is_verified')


class EducationProgramInline(admin.TabularInline):
    model = EducationProgram
    extra = 1
    fields = ('study_form', 'tuition_fee', 'duration', 'is_active')


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
    inlines = [EducationProgramInline]


@admin.register(EducationProgram)
class EducationProgramAdmin(admin.ModelAdmin):
    list_display = ('specialty', 'study_form', 'tuition_fee', 'duration', 'is_active')
    list_filter = ('study_form', 'is_active', 'specialty__faculty')
    search_fields = ('specialty__name', 'specialty__code', 'duration')
    list_editable = ('tuition_fee', 'is_active')


@admin.register(ExamSubject)
class ExamSubjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'min_score')
    search_fields = ('name',)
    list_editable = ('min_score',)


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ('id', 'applicant', 'program', 'financing_type', 'get_total_score', 'status', 'submission_date')
    list_filter = ('status', 'financing_type', 'program__study_form', 'program__specialty__faculty', 'submission_date')
    search_fields = ('applicant__username', 'applicant__first_name', 'applicant__last_name', 'applicant__email', 'program__specialty__name')
    list_editable = ('status', 'financing_type')
    date_hierarchy = 'submission_date'
    inlines = [ApplicationDocumentInline, ExamScoreInline]

    def get_total_score(self, obj):
        return obj.total_score
    get_total_score.short_description = 'Сумма баллов'


@admin.register(ApplicationDocument)
class ApplicationDocumentAdmin(admin.ModelAdmin):
    list_display = ('id', 'application', 'document_type', 'file', 'is_verified', 'uploaded_at')
    list_filter = ('document_type', 'is_verified', 'uploaded_at')
    search_fields = ('application__applicant__username', 'application__applicant__last_name', 'comment')
    list_editable = ('is_verified',)


@admin.register(ExamScore)
class ExamScoreAdmin(admin.ModelAdmin):
    list_display = ('id', 'application', 'subject', 'score', 'exam_type', 'year', 'is_verified')
    list_filter = ('exam_type', 'is_verified', 'subject', 'year')
    search_fields = ('application__applicant__username', 'application__applicant__last_name', 'subject__name', 'document_number')
    list_editable = ('score', 'is_verified')





