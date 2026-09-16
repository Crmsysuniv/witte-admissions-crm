import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from accounts.models import ApplicantProfile
from admissions.models import Faculty, Specialty, EducationProgram, Application, ApplicationDocument, ExamScore
from audit.models import Notification, StatusLog
from .forms import StudentProfileForm, ApplicationSubmissionForm, DocumentUploadForm
from .decorators import applicant_required


@login_required
@applicant_required
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

    active_applications = applications.exclude(status=Application.Status.WITHDRAWN)
    primary_application = active_applications.first() or applications.first()
    total_applications = applications.count()
    active_applications_count = active_applications.count()

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
            'url': '/student/documents/',
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
            'title': 'Конкурс и рейтинг',
            'desc': 'Списки и приказ о зачислении',
            'completed': step6_approval,
            'current': step5_scores and not step6_approval,
            'icon': 'bi-trophy-fill',
            'url': '/student/rating/',
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
            'title': 'Конкурсные списки и рейтинг',
            'desc': 'Отслеживайте позицию в реальном времени и проходной балл',
            'url': '/student/rating/',
            'icon': 'bi-trophy-fill',
            'color': 'indigo',
        },
        {
            'title': 'Документы и сканы',
            'desc': 'Загрузка паспорта, аттестата и проверка файлов',
            'url': '/student/documents/',
            'icon': 'bi-folder-check',
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
        'active_applications': active_applications,
        'active_applications_count': active_applications_count,
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
@applicant_required
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
@applicant_required
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


@login_required
@applicant_required
def documents_view(request):
    """
    Интерфейс загрузки и управления электронными документами/сканами (student/documents.html):
    - Сводка загруженных документов абитуриента с предпросмотром прикрепленных файлов (PDF, JPG, PNG);
    - Статусы верификации документов сотрудниками приемной комиссии;
    - Форма загрузки новых сканов с валидацией размера и типа файлов;
    - Возможность удаления непринятых / устаревших документов;
    - Чек-лист комплектности досье абитуриента.
    """
    user = request.user
    applicant_profile = getattr(user, 'applicant_profile', None)

    applications = (
        Application.objects.filter(applicant=user)
        .select_related('program__specialty__faculty', 'program')
        .order_by('-submission_date')
    )

    documents = (
        ApplicationDocument.objects.filter(application__applicant=user)
        .select_related('application__program__specialty')
        .order_by('-uploaded_at')
    )

    # Обработка удаления документа
    if request.method == 'POST' and request.POST.get('action') == 'delete':
        doc_id = request.POST.get('document_id')
        doc = get_object_or_404(ApplicationDocument, id=doc_id, application__applicant=user)
        doc_type_title = doc.get_document_type_display()
        doc.file.delete(save=False)
        doc.delete()
        messages.success(request, f'Документ «{doc_type_title}» успешно удален.')
        return redirect('student:documents')

    # Обработка загрузки нового документа
    if request.method == 'POST':
        if not applications.exists():
            messages.error(request, 'Для загрузки документов необходимо сначала подать хотя бы одно заявление.')
            return redirect('student:apply')

        form = DocumentUploadForm(request.POST, request.FILES, user=user)
        if form.is_valid():
            document = form.save()

            # Уведомление для абитуриента
            Notification.objects.create(
                user=user,
                notification_type=Notification.NotificationType.DOCUMENT,
                title='Документ прикреплен к заявлению',
                message=(
                    f'Скан «{document.get_document_type_display()}» успешно прикреплен к заявлению №{document.application_id} '
                    f'на направление «{document.application.program.specialty.name}» и передан на проверку.'
                )
            )

            messages.success(
                request,
                f'Документ «{document.get_document_type_display()}» успешно загружен и ожидает проверки комиссией!'
            )
            return redirect('student:documents')
        else:
            messages.error(request, 'Пожалуйста, проверьте правильность заполнения полей и размер прикрепленного файла.')
    else:
        form = DocumentUploadForm(user=user)

    # Расчет статистики комплектности досье
    total_documents = documents.count()
    verified_count = documents.filter(is_verified=True).count()
    pending_count = total_documents - verified_count

    has_passport = documents.filter(document_type=ApplicationDocument.DocumentType.PASSPORT).exists()
    has_education_doc = documents.filter(
        document_type__in=[ApplicationDocument.DocumentType.CERTIFICATE, ApplicationDocument.DocumentType.DIPLOMA]
    ).exists()
    has_privilege = documents.filter(document_type=ApplicationDocument.DocumentType.PRIVILEGE).exists()
    has_other = documents.filter(document_type=ApplicationDocument.DocumentType.OTHER).exists()

    # Прогресс комплектности документов (0-100%)
    readiness_percentage = 0
    if has_passport:
        readiness_percentage += 50
    if has_education_doc:
        readiness_percentage += 50

    context = {
        'form': form,
        'documents': documents,
        'applications': applications,
        'total_documents': total_documents,
        'verified_count': verified_count,
        'pending_count': pending_count,
        'has_passport': has_passport,
        'has_education_doc': has_education_doc,
        'has_privilege': has_privilege,
        'has_other': has_other,
        'readiness_percentage': readiness_percentage,
        'applicant_profile': applicant_profile,
    }
    return render(request, 'student/documents.html', context)


@login_required
@applicant_required
def rating_view(request):
    """
    Страница отслеживания конкурсных списков и позиций в рейтинге (student/rating.html):
    - Персональная сводка конкурсных позиций текущего абитуриента;
    - Официальные конкурсные списки поступающих с детализацией по баллам;
    - Обезличенные идентификаторы абитуриентов (СНИЛС или номер заявления согласно ФЗ-152);
    - Выделение черты контрольных цифр приема («зеленая зона» плана набора);
    - Фильтрация по специальностям, форме финансирования (бюджет / договор), оригиналам документов;
    - Подсчет текущего проходного балла, конкурса (человек на место) и прогноза шансов.
    """
    user = request.user

    # 1. Поданные заявления текущего пользователя
    user_applications = (
        Application.objects.filter(applicant=user)
        .select_related('program__specialty__faculty', 'program')
        .prefetch_related('exam_scores__subject', 'documents')
        .order_by('-submission_date')
    )

    # 2. Расчет персональных позиций пользователя в каждом конкурсе
    user_rankings_summary = []
    for app in user_applications:
        app_financing = app.financing_type
        app_program = app.program
        specialty = app_program.specialty

        places_count = specialty.budget_places if app_financing == Application.FinancingType.BUDGET else specialty.paid_places

        # Конкурсные заявления по той же программе и основе
        competing_qs = (
            Application.objects.filter(
                program=app_program,
                financing_type=app_financing,
            )
            .exclude(status__in=[Application.Status.DRAFT, Application.Status.REJECTED, Application.Status.WITHDRAWN])
            .prefetch_related('exam_scores')
        )

        # Вычисляем баллы каждого участника для определения точного ранга
        ranked_apps = []
        for c_app in competing_qs:
            total_sc = sum(s.score for s in c_app.exam_scores.all())
            ranked_apps.append((c_app.id, total_sc, c_app.submission_date))

        # Сортировка: по убыванию баллов, затем по дате подачи
        ranked_apps.sort(key=lambda x: (-x[1], x[2]))

        # Поиск ранга заявления пользователя
        user_rank = None
        user_total_score = app.total_score
        for idx, (c_id, c_score, _) in enumerate(ranked_apps, start=1):
            if c_id == app.id:
                user_rank = idx
                user_total_score = c_score
                break

        total_in_comp = len(ranked_apps)
        in_quota = (user_rank is not None and user_rank <= places_count) if places_count > 0 else False

        user_rankings_summary.append({
            'application': app,
            'program': app_program,
            'specialty': specialty,
            'financing_type': app_financing,
            'financing_display': app.get_financing_type_display(),
            'user_rank': user_rank,
            'total_applicants': total_in_comp,
            'places_count': places_count,
            'total_score': user_total_score,
            'in_quota': in_quota,
            'status': app.status,
            'status_display': app.get_status_display(),
        })

    # 3. Фильтры для просмотра конкурсного списка
    program_id = request.GET.get('program')
    financing_type = request.GET.get('financing', Application.FinancingType.BUDGET)
    only_originals = request.GET.get('originals') == '1'
    search_query = request.GET.get('q', '').strip()

    # Список всех активных программ для переключателя
    all_programs = (
        EducationProgram.objects.filter(is_active=True)
        .select_related('specialty__faculty')
        .order_by('specialty__faculty__name', 'specialty__name', 'study_form')
    )

    # Выбор активной программы
    selected_program = None
    if program_id:
        selected_program = EducationProgram.objects.filter(id=program_id, is_active=True).first()

    if not selected_program and user_applications.exists():
        selected_program = user_applications.first().program

    if not selected_program:
        selected_program = all_programs.first()

    # 4. Формирование конкурсного списка для выбранной программы
    ranked_candidates = []
    places_count = 0
    competition_ratio = 0.0
    passing_score = 0
    user_in_list = None

    if selected_program:
        specialty = selected_program.specialty
        places_count = specialty.budget_places if financing_type == Application.FinancingType.BUDGET else specialty.paid_places

        base_candidates_qs = (
            Application.objects.filter(
                program=selected_program,
                financing_type=financing_type,
            )
            .exclude(status__in=[Application.Status.DRAFT, Application.Status.REJECTED, Application.Status.WITHDRAWN])
            .select_related('applicant', 'applicant__applicant_profile', 'program__specialty')
            .prefetch_related('exam_scores__subject', 'documents')
        )

        temp_list = []
        for c_app in base_candidates_qs:
            applicant = c_app.applicant
            profile = getattr(applicant, 'applicant_profile', None)

            # Обезличенный идентификатор: СНИЛС или номер заявки
            if profile and profile.snils:
                raw_snils = profile.snils.strip()
                snils_display = raw_snils
            else:
                snils_display = f"№ 2026-{c_app.id:04d}"

            # Детализация экзаменационных баллов
            scores = list(c_app.exam_scores.all())
            scores_total = sum(s.score for s in scores)
            scores_detail = [
                {
                    'subject': s.subject.name,
                    'score': s.score,
                    'is_passing': s.score >= s.subject.min_score,
                    'is_verified': s.is_verified,
                }
                for s in scores
            ]

            # Наличие оригинала документа об образовании
            has_original = c_app.documents.filter(
                document_type__in=[ApplicationDocument.DocumentType.CERTIFICATE, ApplicationDocument.DocumentType.DIPLOMA]
            ).exists()

            is_current = (applicant.id == user.id)

            temp_list.append({
                'app_id': c_app.id,
                'applicant_name': applicant.get_full_name() or applicant.username,
                'snils': snils_display,
                'total_score': scores_total,
                'scores_detail': scores_detail,
                'has_original': has_original,
                'is_current_user': is_current,
                'submission_date': c_app.submission_date,
                'status': c_app.status,
                'status_display': c_app.get_status_display(),
            })

        # Ранжирование по баллам (убывание), затем дате
        temp_list.sort(key=lambda x: (-x['total_score'], x['submission_date']))

        # Присваиваем ранги и флаг попадания в контрольные цифры приема
        for idx, item in enumerate(temp_list, start=1):
            item['rank'] = idx
            item['in_quota'] = (idx <= places_count) if places_count > 0 else False
            if item['is_current_user']:
                user_in_list = item
            ranked_candidates.append(item)

        total_applicants = len(ranked_candidates)
        originals_count = sum(1 for c in ranked_candidates if c['has_original'])
        competition_ratio = round(total_applicants / places_count, 2) if places_count > 0 else 0.0

        # Текущий проходной балл
        if total_applicants > 0:
            if places_count > 0 and total_applicants >= places_count:
                passing_score = ranked_candidates[places_count - 1]['total_score']
            else:
                passing_score = ranked_candidates[-1]['total_score']
        else:
            passing_score = 0
    else:
        total_applicants = 0
        originals_count = 0

    # 5. Применение клиентских фильтров к списку
    displayed_candidates = ranked_candidates

    if only_originals:
        displayed_candidates = [c for c in displayed_candidates if c['has_original']]

    if search_query:
        sq = search_query.lower()
        displayed_candidates = [
            c for c in displayed_candidates
            if sq in c['snils'].lower() or sq in str(c['app_id']) or (c['is_current_user'] and sq in 'вы')
        ]

    context = {
        'user_rankings_summary': user_rankings_summary,
        'all_programs': all_programs,
        'selected_program': selected_program,
        'selected_financing': financing_type,
        'only_originals': only_originals,
        'search_query': search_query,
        'places_count': places_count,
        'total_applicants': total_applicants,
        'originals_count': originals_count,
        'competition_ratio': competition_ratio,
        'passing_score': passing_score,
        'user_in_list': user_in_list,
        'displayed_candidates': displayed_candidates,
    }
    return render(request, 'student/rating.html', context)


@login_required
@applicant_required
def withdraw_application_view(request, application_id):
    """
    Отзыв поданного заявления абитуриентом (с подтверждением действия).
    - Доступ только авторизованному владельцу заявления (applicant=request.user);
    - Защита от повторного отзыва и отзыва уже зачисленных заявлений;
    - Фиксация смены статуса на WITHDRAWN;
    - Создание записи аудита в StatusLog с причиной отзыва;
    - Отправка системного уведомления в Notification;
    - Отображение Flash-сообщения об успешном отзыве заявления;
    - Модальное подтверждение или отдельная страница подтверждения при прямом GET-переходе.
    """
    user = request.user
    application = get_object_or_404(
        Application.objects.select_related('program__specialty__faculty', 'program'),
        id=application_id,
        applicant=user
    )

    # Проверка возможности отзыва
    if application.status == Application.Status.WITHDRAWN:
        messages.warning(request, f'Заявление №{application.id} уже было отозвано ранее.')
        return redirect('student:dashboard')

    if application.status == Application.Status.ENROLLED:
        messages.error(
            request,
            f'Невозможно отозвать заявление №{application.id}: вы уже зачислены приказом ректора. '
            f'Для решения вопроса об отчислении обратитесь в студенческий отдел кадров МУ им. С.Ю. Витте.'
        )
        return redirect('student:dashboard')

    if request.method == 'POST':
        reason = request.POST.get('withdrawal_reason', '').strip()
        custom_comment = request.POST.get('custom_comment', '').strip()

        comment_parts = []
        if reason:
            comment_parts.append(reason)
        if custom_comment:
            comment_parts.append(custom_comment)

        full_comment = " — ".join(comment_parts) if comment_parts else "Заявление отозвано абитуриентом по собственному желанию."

        old_status = application.status
        application.status = Application.Status.WITHDRAWN
        application.officer_comment = f"Отозвано абитуриентом: {full_comment}"
        application.save()

        # 1. Запись в журнал аудита изменений статусов
        StatusLog.objects.create(
            application=application,
            old_status=old_status,
            new_status=Application.Status.WITHDRAWN,
            changed_by=user,
            comment=full_comment
        )

        # 2. Создание уведомления в личном кабинете
        Notification.objects.create(
            user=user,
            title='Заявление успешно отозвано',
            message=f'Вы успешно отозвали заявление №{application.id} на направление «{application.program.specialty.name}» ({application.program.get_study_form_display()} форма).',
            notification_type=Notification.NotificationType.STATUS_CHANGE
        )

        messages.success(
            request,
            f'Заявление №{application.id} на программу «{application.program.specialty.name}» успешно отозвано.'
        )

        next_url = request.POST.get('next')
        if next_url:
            return redirect(next_url)
        return redirect('student:dashboard')

    # GET-запрос: отображение страницы подтверждения отзыва
    context = {
        'application': application,
        'program': application.program,
        'specialty': application.program.specialty,
    }
    return render(request, 'student/application_confirm_withdraw.html', context)


@login_required
@applicant_required
def export_rating_xlsx_view(request):
    """
    Экспорт конкурсного списка для абитуриента в формате Excel (.xlsx).
    """
    from admissions.exports import export_rating_xlsx_response

    program_id = request.GET.get('program')
    financing_type = request.GET.get('financing', Application.FinancingType.BUDGET)
    only_originals = request.GET.get('originals') in ['1', 'true', 'True']

    selected_program = None
    if program_id and str(program_id).isdigit():
        selected_program = EducationProgram.objects.filter(id=program_id, is_active=True).first()

    if not selected_program:
        user_apps = Application.objects.filter(applicant=request.user).exclude(status=Application.Status.WITHDRAWN)
        if user_apps.exists():
            selected_program = user_apps.first().program
        else:
            selected_program = EducationProgram.objects.filter(is_active=True).first()

    if not selected_program:
        messages.error(request, 'Не найдено программы для экспорта конкурсного списка.')
        return redirect('student:rating')

    return export_rating_xlsx_response(
        program=selected_program,
        financing_type=financing_type,
        only_originals=only_originals,
        is_officer=False
    )






