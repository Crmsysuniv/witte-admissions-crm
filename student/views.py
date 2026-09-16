import json
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from accounts.models import ApplicantProfile
from admissions.models import Faculty, Specialty, EducationProgram, Application, ApplicationDocument, ExamScore
from audit.models import Notification, StatusLog
from .forms import StudentProfileForm, ApplicationSubmissionForm


@login_required
def dashboard_view(request):
    """
    Дашборд абитуриента (student/dashboard.html):
    - Сводка текущего статуса поступления и деталей заявления;
    - Пошаговый прогресс-бар этапов поступления (от регистрации до приказа о зачислении);
    - Быстрые ссылки на ключевые сервисы и подачу документов;
    - Статистика поданных заявлений, прикрепленных сканов и баллов ЕГЭ;
    - Персональные уведомления приемной комиссии.
    """
    user = request.user
    applicant_profile = getattr(user, 'applicant_profile', None)

    # Список поданных заявлений абитуриента
    applications = (
        Application.objects.filter(applicant=user)
        .select_related('program__specialty__faculty', 'program')
        .prefetch_related('documents', 'exam_scores__subject')
        .order_by('-submission_date')
    )

    primary_application = applications.first()
    total_applications = applications.count()

    # Документы и сканы
    user_documents = ApplicationDocument.objects.filter(application__applicant=user)
    total_documents = user_documents.count()
    verified_documents_count = user_documents.filter(is_verified=True).count()

    # Баллы вступительных испытаний и ЕГЭ
    user_scores = ExamScore.objects.filter(application__applicant=user).select_related('subject')
    total_score = sum(s.score for s in user_scores) if user_scores.exists() else 0

    # Уведомления абитуриента
    notifications = Notification.objects.filter(user=user).order_by('-created_at')[:5]
    unread_notifications_count = Notification.objects.filter(user=user, is_read=False).count()

    # Расчет этапов прогресс-бара
    step1_account = True
    step2_profile = bool(applicant_profile and (applicant_profile.snils or applicant_profile.passport_number))
    step3_application = total_applications > 0
    step4_documents = total_documents >= 1
    step5_scores = user_scores.exists()
    step6_approval = False

    if primary_application:
        if primary_application.status in [Application.Status.APPROVED, Application.Status.ENROLLED]:
            step6_approval = True

    steps = [
        {
            'num': 1,
            'title': 'Личный кабинет',
            'desc': 'Регистрация учетной записи',
            'completed': step1_account,
            'current': not step2_profile,
            'icon': 'bi-person-check-fill',
            'url': '/student/dashboard/',
        },
        {
            'num': 2,
            'title': 'Анкета абитуриента',
            'desc': 'Паспортные данные и СНИЛС',
            'completed': step2_profile,
            'current': step1_account and not step2_profile,
            'icon': 'bi-card-text',
            'url': '/student/profile/',
        },
        {
            'num': 3,
            'title': 'Подача заявления',
            'desc': 'Выбор программ обучения',
            'completed': step3_application,
            'current': step2_profile and not step3_application,
            'icon': 'bi-file-earmark-plus-fill',
            'url': '/student/apply/',
        },
        {
            'num': 4,
            'title': 'Загрузка документов',
            'desc': 'Скан паспорта и аттестата',
            'completed': step4_documents,
            'current': step3_application and not step4_documents,
            'icon': 'bi-folder-check',
            'url': '/admin/admissions/applicationdocument/',
        },
        {
            'num': 5,
            'title': 'Баллы ЕГЭ / ВИ',
            'desc': 'Внесение результатов экзаменов',
            'completed': step5_scores,
            'current': step4_documents and not step5_scores,
            'icon': 'bi-award-fill',
            'url': '/calculator/',
        },
        {
            'num': 6,
            'title': 'Допуск к конкурсу',
            'desc': 'Приказ о зачислении',
            'completed': step6_approval,
            'current': step5_scores and not step6_approval,
            'icon': 'bi-patch-check-fill',
            'url': '/rules/',
        },
    ]

    completed_steps_count = sum(1 for s in steps if s['completed'])
    progress_percentage = int((completed_steps_count / len(steps)) * 100)

    # Статусы заявлений с метаданными стилей
    status_config = {
        'DRAFT': {
            'label': 'Черновик',
            'badge': 'bg-slate-100 text-slate-700 border-slate-300',
            'indicator': 'bg-slate-400',
            'desc': 'Заявление сохранено в черновиках. Завершите заполнение и отправьте на рассмотрение.',
        },
        'SUBMITTED': {
            'label': 'Подано в комиссию',
            'badge': 'bg-blue-100 text-blue-800 border-blue-300',
            'indicator': 'bg-blue-500',
            'desc': 'Заявление успешно принято сервером CRM и поставлено в очередь на первичную проверку.',
        },
        'UNDER_REVIEW': {
            'label': 'На рассмотрении',
            'badge': 'bg-amber-100 text-amber-900 border-amber-300',
            'indicator': 'bg-amber-500',
            'desc': 'Сотрудник приемной комиссии проверяет комплект документов и соответствие вступительных баллов.',
        },
        'DOCUMENTS_REQUIRED': {
            'label': 'Требуются документы',
            'badge': 'bg-rose-100 text-rose-800 border-rose-300',
            'indicator': 'bg-rose-500',
            'desc': 'Необходимо прикрепить недостающие сканы документов в соответствии с комментарием комиссии.',
        },
        'APPROVED': {
            'label': 'Допущен к конкурсу',
            'badge': 'bg-emerald-100 text-emerald-900 border-emerald-300',
            'indicator': 'bg-emerald-500',
            'desc': 'Документы и баллы проверены. Заявление допущено к конкурсному отбору и ранжированию.',
        },
        'ENROLLED': {
            'label': 'Зачислен приказом',
            'badge': 'bg-purple-100 text-purple-900 border-purple-300',
            'indicator': 'bg-purple-500',
            'desc': 'Поздравляем! Издан официальный приказ о зачислении в число студентов МУ им. С.Ю. Витте!',
        },
        'REJECTED': {
            'label': 'Отклонено',
            'badge': 'bg-rose-100 text-rose-800 border-rose-300',
            'indicator': 'bg-rose-500',
            'desc': 'Заявление отклонено приемной комиссией. Ознакомьтесь с причиной в комментарии сотрудника.',
        },
        'WITHDRAWN': {
            'label': 'Отозвано заявителем',
            'badge': 'bg-slate-100 text-slate-700 border-slate-300',
            'indicator': 'bg-slate-400',
            'desc': 'Заявление отозвано по запросу абитуриента.',
        },
    }

    current_status_info = None
    if primary_application:
        current_status_info = status_config.get(primary_application.status, {
            'label': primary_application.get_status_display(),
            'badge': 'bg-blue-100 text-blue-800 border-blue-300',
            'indicator': 'bg-blue-500',
            'desc': 'Заявление обрабатывается приемной комиссией университета.',
        })

    # Быстрые ссылки для абитуриента
    quick_links = [
        {
            'title': 'Анкета и личные данные',
            'desc': 'Паспортные данные, СНИЛС и адрес регистрации',
            'url': '/student/profile/',
            'icon': 'bi-person-vcard-fill',
            'color': 'indigo',
        },
        {
            'title': 'Каталог программ 2026',
            'desc': 'Специальности бакалавриата, специалитета и колледжа',
            'url': '/programs/',
            'icon': 'bi-journal-bookmark-fill',
            'color': 'blue',
        },
        {
            'title': 'Калькулятор баллов ЕГЭ',
            'desc': 'Проверьте шансы на бюджет и платное обучение',
            'url': '/calculator/',
            'icon': 'bi-calculator-fill',
            'color': 'cyan',
        },
        {
            'title': 'Правила приема и квоты',
            'desc': 'Сроки подачи документов, учет достижений и льготы',
            'url': '/rules/',
            'icon': 'bi-file-earmark-text-fill',
            'color': 'emerald',
        },
        {
            'title': 'Стоимость и скидка 20%',
            'desc': 'Расчет стоимости семестра и кредит под 3%',
            'url': '/tuition/',
            'icon': 'bi-tag-fill',
            'color': 'amber',
        },
        {
            'title': 'Общежитие и кампус',
            'desc': '100% гарантия мест иногородним первокурсникам',
            'url': '/dormitory/',
            'icon': 'bi-houses-fill',
            'color': 'teal',
        },
        {
            'title': 'Задать вопрос комиссии',
            'desc': 'Оперативная связь со специалистом приемной комиссии',
            'url': '/feedback/',
            'icon': 'bi-chat-left-dots-fill',
            'color': 'rose',
        },
        {
            'title': 'Безопасность и пароль',
            'desc': 'Управление доступом и смена пароля учетной записи',
            'url': '/password_change/',
            'icon': 'bi-shield-lock-fill',
            'color': 'purple',
        },
    ]

    context = {
        'applicant_profile': applicant_profile,
        'applications': applications,
        'primary_application': primary_application,
        'total_applications': total_applications,
        'total_documents': total_documents,
        'verified_documents_count': verified_documents_count,
        'user_scores': user_scores,
        'total_score': total_score,
        'notifications': notifications,
        'unread_notifications_count': unread_notifications_count,
        'steps': steps,
        'completed_steps_count': completed_steps_count,
        'progress_percentage': progress_percentage,
        'current_status_info': current_status_info,
        'status_config': status_config,
        'quick_links': quick_links,
    }
    return render(request, 'student/dashboard.html', context)


@login_required
def profile_view(request):
    """
    Страница заполнения и редактирования персональных данных профиля абитуриента (student/profile.html).
    Позволяет актуализировать:
    - Фамилию, Имя, Отчество, Email, Телефон;
    - Дату рождения, СНИЛС;
    - Паспортные данные гражданина РФ (серия, номер, кем и когда выдан, код подразделения);
    - Адрес постоянной регистрации и фактического проживания.
    """
    user = request.user
    profile, _ = ApplicantProfile.objects.get_or_create(user=user)

    if request.method == 'POST':
        form = StudentProfileForm(request.POST, user=user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Персональные данные профиля успешно сохранены и обновлены!')
            return redirect('student:profile')
        else:
            messages.error(request, 'Пожалуйста, проверьте правильность заполнения обязательных полей.')
    else:
        form = StudentProfileForm(user=user)

    # Расчет прогресса заполненности профиля
    sections = {
        'contacts': bool(user.first_name and user.last_name and user.email and user.phone),
        'identity': bool(profile.birth_date and profile.snils),
        'passport': bool(profile.passport_series and profile.passport_number and profile.passport_issued_by and profile.passport_issue_date and profile.passport_department_code),
        'address': bool(profile.address),
    }

    # Вес секций в %: контакты 25%, СНИЛС/дата 25%, паспорт 35%, адрес 15%
    completion_percentage = (
        (25 if sections['contacts'] else 0) +
        (25 if sections['identity'] else 0) +
        (35 if sections['passport'] else 0) +
        (15 if sections['address'] else 0)
    )

    context = {
        'form': form,
        'applicant_profile': profile,
        'sections': sections,
        'completion_percentage': completion_percentage,
    }
    return render(request, 'student/profile.html', context)


@login_required
def apply_view(request):
    """
    Пошаговая форма подачи заявления на обучение (student/apply.html):
    - Выбор факультета / института (Шаг 1);
    - Выбор направления подготовки (Шаг 2);
    - Выбор формы обучения и программы (Шаг 3);
    - Выбор основы финансирования (бюджет / платная) и согласия (Шаг 4);
    - Финальная проверка параметров и отправка заявления (Шаг 5).
    """
    user = request.user
    applicant_profile = getattr(user, 'applicant_profile', None)

    existing_applications = (
        Application.objects.filter(applicant=user)
        .select_related('program__specialty__faculty', 'program')
        .order_by('-submission_date')
    )
    total_existing = existing_applications.count()
    max_applications = 5
    remaining_slots = max(0, max_applications - total_existing)
    can_apply = remaining_slots > 0

    initial_faculty_id = request.POST.get('faculty') if request.method == 'POST' else request.GET.get('faculty', '')
    initial_specialty_id = request.POST.get('specialty') if request.method == 'POST' else request.GET.get('specialty', '')
    initial_program_id = request.POST.get('program') if request.method == 'POST' else request.GET.get('program', '')

    if request.method == 'POST':
        if not can_apply:
            messages.error(
                request,
                'Вы достигли максимального лимита заявлений (5 из 5) в рамках приемной кампании 2026 года.'
            )
            return redirect('student:dashboard')

        form = ApplicationSubmissionForm(request.POST, user=user)
        if form.is_valid():
            program = form.cleaned_data['program']
            financing_type = form.cleaned_data['financing_type']

            # Создание заявления
            application = Application.objects.create(
                applicant=user,
                program=program,
                financing_type=financing_type,
                status=Application.Status.SUBMITTED,
            )

            # Запись в историю аудита статусов
            StatusLog.objects.create(
                application=application,
                old_status='',
                new_status=Application.Status.SUBMITTED,
                changed_by=user,
                comment='Электронное заявление успешно подано абитуриентом через личный кабинет.',
            )

            # Персональное уведомление абитуриенту
            Notification.objects.create(
                user=user,
                notification_type=Notification.NotificationType.SUCCESS,
                title=f'Заявление №{application.id} принято в комиссию',
                message=(
                    f'Ваше заявление на направление «{program.specialty.code} {program.specialty.name}» '
                    f'({program.get_study_form_display()}, {application.get_financing_type_display()}) '
                    f'успешно зарегистрировано в CRM и направлено на проверку.'
                ),
            )

            messages.success(
                request,
                f'Заявление №{application.id} на направление «{program.specialty.name}» успешно подано в приемную комиссию!'
            )
            return redirect('student:dashboard')
        else:
            messages.error(request, 'Пожалуйста, проверьте правильность заполнения полей заявления.')
    else:
        initial_data = {}
        if initial_program_id and str(initial_program_id).isdigit():
            prog = EducationProgram.objects.filter(id=initial_program_id, is_active=True).select_related('specialty__faculty').first()
            if prog:
                initial_data['program'] = prog.id
                initial_data['specialty'] = prog.specialty_id
                initial_data['faculty'] = prog.specialty.faculty_id
                initial_faculty_id = str(prog.specialty.faculty_id)
                initial_specialty_id = str(prog.specialty_id)
        elif initial_specialty_id and str(initial_specialty_id).isdigit():
            spec = Specialty.objects.filter(id=initial_specialty_id, is_active=True).first()
            if spec:
                initial_data['specialty'] = spec.id
                initial_data['faculty'] = spec.faculty_id
                initial_faculty_id = str(spec.faculty_id)

        form = ApplicationSubmissionForm(user=user, initial=initial_data)

    # Подготовка данных для визарда на Alpine.js
    faculties = Faculty.objects.prefetch_related('specialties__programs').all()
    faculties_data = [
        {
            'id': f.id,
            'name': f.name,
            'code': f.code or f.name[:4].upper(),
            'description': f.description,
            'specialties_count': f.specialties.filter(is_active=True).count(),
        }
        for f in faculties if f.specialties.filter(is_active=True).exists()
    ]

    specialties = Specialty.objects.filter(is_active=True).select_related('faculty').prefetch_related('programs')
    specialties_data = [
        {
            'id': s.id,
            'faculty_id': s.faculty_id,
            'faculty_name': s.faculty.name,
            'code': s.code,
            'name': s.name,
            'education_level': s.education_level,
            'education_level_display': s.get_education_level_display(),
            'budget_places': s.budget_places,
            'paid_places': s.paid_places,
            'total_places': s.total_places,
            'programs_count': s.programs.filter(is_active=True).count(),
        }
        for s in specialties if s.programs.filter(is_active=True).exists()
    ]

    programs = EducationProgram.objects.filter(is_active=True).select_related('specialty__faculty')
    programs_data = [
        {
            'id': p.id,
            'specialty_id': p.specialty_id,
            'faculty_id': p.specialty.faculty_id,
            'study_form': p.study_form,
            'study_form_display': p.get_study_form_display(),
            'duration': p.duration,
            'tuition_fee': float(p.tuition_fee),
            'tuition_fee_formatted': f"{int(p.tuition_fee):,} ₽/год".replace(',', ' '),
            'tuition_fee_discounted': float(p.tuition_fee) * 0.8,
            'tuition_fee_discounted_formatted': f"{int(float(p.tuition_fee) * 0.8):,} ₽/год".replace(',', ' '),
        }
        for p in programs
    ]

    context = {
        'form': form,
        'applicant_profile': applicant_profile,
        'total_existing': total_existing,
        'max_applications': max_applications,
        'remaining_slots': remaining_slots,
        'can_apply': can_apply,
        'existing_applications': existing_applications,
        'faculties_json': json.dumps(faculties_data, ensure_ascii=False),
        'specialties_json': json.dumps(specialties_data, ensure_ascii=False),
        'programs_json': json.dumps(programs_data, ensure_ascii=False),
        'initial_faculty_id': initial_faculty_id or '',
        'initial_specialty_id': initial_specialty_id or '',
        'initial_program_id': initial_program_id or '',
    }
    return render(request, 'student/apply.html', context)


