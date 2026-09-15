from django.shortcuts import render
from django.db.models import Sum
from admissions.models import Faculty, Specialty, EducationProgram, ExamSubject


def home(request):
    """
    Главная публичная страница приемной кампании 2026 МУ им. С.Ю. Витте.
    """
    faculties = Faculty.objects.prefetch_related('specialties').all()
    specialties = Specialty.objects.filter(is_active=True).select_related('faculty')
    programs = EducationProgram.objects.filter(is_active=True).select_related('specialty')
    subjects = ExamSubject.objects.all()

    total_budget_places = specialties.aggregate(total=Sum('budget_places'))['total'] or 0
    total_paid_places = specialties.aggregate(total=Sum('paid_places'))['total'] or 0

    timeline_events = [
        {
            'date': '20 июня 2026',
            'badge': 'Старт кампании',
            'title': 'Начало приема документов',
            'description': 'Открытие онлайн-подачи заявлений через CRM-портал и очного приема в главном кампусе.',
            'status': 'completed',
            'icon': 'bi-flag-fill',
            'color': 'emerald',
        },
        {
            'date': '10 июля 2026',
            'badge': 'Вступительные',
            'title': 'Окончание приема документов с ВИ',
            'description': 'Завершение подачи заявлений для поступающих по внутренним вступительным испытаниям вуза.',
            'status': 'upcoming',
            'icon': 'bi-pencil-square',
            'color': 'blue',
        },
        {
            'date': '25 июля 2026',
            'badge': 'Бюджет ЕГЭ',
            'title': 'Завершение приема на бюджет',
            'description': 'Финальный день подачи документов для поступающих по результатам ЕГЭ на бюджетные места.',
            'status': 'upcoming',
            'icon': 'bi-calendar-check-fill',
            'color': 'indigo',
        },
        {
            'date': '27 июля 2026',
            'badge': 'Рейтинги',
            'title': 'Публикация конкурсных списков',
            'description': 'Размещение официальных рейтинговых списков с баллами и ранжированием абитуриентов.',
            'status': 'upcoming',
            'icon': 'bi-bar-chart-line-fill',
            'color': 'amber',
        },
        {
            'date': '03 августа 2026',
            'badge': 'Зачисление',
            'title': 'Приказы о зачислении (Бюджет)',
            'description': 'Издание приказов о зачислении абитуриентов на бюджетные места очной и заочной формы.',
            'status': 'upcoming',
            'icon': 'bi-award-fill',
            'color': 'purple',
        },
        {
            'date': '28 августа 2026',
            'badge': 'Договор',
            'title': 'Зачисление на платное обучение',
            'description': 'Завершение заключения договоров об оказании платных образовательных услуг и приказы.',
            'status': 'upcoming',
            'icon': 'bi-check-all',
            'color': 'teal',
        },
    ]

    context = {
        'faculties': faculties,
        'specialties': specialties,
        'programs': programs,
        'subjects': subjects,
        'total_budget_places': total_budget_places,
        'total_paid_places': total_paid_places,
        'timeline_events': timeline_events,
    }
    return render(request, 'home.html', context)

