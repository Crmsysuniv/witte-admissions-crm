from django.shortcuts import render, get_object_or_404
from django.db.models import Q, Count
from .models import Faculty, Specialty, EducationProgram, ExamSubject


def faculties_list(request):
    """
    Каталог факультетов и институтов МУ им. С.Ю. Витте.
    """
    faculties = Faculty.objects.prefetch_related('specialties__programs').all()
    
    total_specialties = Specialty.objects.filter(is_active=True).count()
    total_programs = EducationProgram.objects.filter(is_active=True).count()

    context = {
        'faculties': faculties,
        'total_specialties': total_specialties,
        'total_programs': total_programs,
    }
    return render(request, 'faculties_list.html', context)


def programs_catalog(request):
    """
    Каталог образовательных программ и направлений обучения с фильтрами по формам обучения,
    факультетам и уровню образования.
    """
    study_form_filter = request.GET.get('study_form', '')
    faculty_filter = request.GET.get('faculty', '')
    level_filter = request.GET.get('level', '')
    search_query = request.GET.get('q', '').strip()

    programs = EducationProgram.objects.filter(is_active=True).select_related('specialty', 'specialty__faculty')

    if study_form_filter:
        programs = programs.filter(study_form=study_form_filter)

    if faculty_filter:
        programs = programs.filter(specialty__faculty_id=faculty_filter)

    if level_filter:
        programs = programs.filter(specialty__education_level=level_filter)

    if search_query:
        programs = programs.filter(
            Q(specialty__name__icontains=search_query) |
            Q(specialty__code__icontains=search_query) |
            Q(specialty__faculty__name__icontains=search_query)
        )

    faculties = Faculty.objects.all()
    study_forms = EducationProgram.StudyForm.choices
    education_levels = Specialty.EducationLevel.choices
    exam_subjects = ExamSubject.objects.all()

    context = {
        'programs': programs,
        'faculties': faculties,
        'study_forms': study_forms,
        'education_levels': education_levels,
        'exam_subjects': exam_subjects,
        'selected_study_form': study_form_filter,
        'selected_faculty': faculty_filter,
        'selected_level': level_filter,
        'search_query': search_query,
        'total_found': programs.count(),
    }
    return render(request, 'programs_catalog.html', context)


def specialty_detail(request, pk):
    """
    Детальная страница конкретного направления подготовки.
    """
    specialty = get_object_or_404(Specialty.objects.select_related('faculty'), pk=pk)
    programs = specialty.programs.filter(is_active=True)
    subjects = ExamSubject.objects.all()

    context = {
        'specialty': specialty,
        'programs': programs,
        'subjects': subjects,
    }
    return render(request, 'specialty_detail.html', context)
