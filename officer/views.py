from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Count, Sum
from django.core.paginator import Paginator
from django.utils import timezone

from .decorators import officer_required
from admissions.models import Application, ApplicationDocument, Faculty, Specialty, EducationProgram, ExamScore
from audit.models import StatusLog, Notification
from accounts.models import OfficerProfile
from feedback.models import FeedbackMessage


@login_required
@officer_required
def workplace_view(request):
    """
    Рабочий стол сотрудника приемной комиссии.
    Отображает сводку входящей очереди заявлений, статистику обработки,
    фильтрацию по статусам, факультетам, типам финансирования,
    поисковую строку и быстрые действия проверки.
    """
    user = request.user
    officer_profile = getattr(user, 'officer_profile', None)

    # Обработка POST-действий (быстрое изменение статуса заявления или верификация)
    if request.method == 'POST':
        action = request.POST.get('action')
        application_id = request.POST.get('application_id')

        if application_id:
            application = get_object_or_404(Application, pk=application_id)

            if action == 'change_status':
                new_status = request.POST.get('new_status')
                officer_comment = request.POST.get('officer_comment', '').strip()
                valid_statuses = dict(Application.Status.choices)

                if new_status in valid_statuses and new_status != application.status:
                    old_status = application.status
                    old_status_display = application.get_status_display()
                    application.status = new_status
                    if officer_comment:
                        application.officer_comment = officer_comment
                    application.save()

                    new_status_display = application.get_status_display()

                    # Аудит изменения статуса
                    StatusLog.objects.create(
                        application=application,
                        old_status=old_status,
                        new_status=new_status,
                        changed_by=user,
                        comment=officer_comment or f'Статус изменен сотрудником {user.get_full_name() or user.username} из рабочего стола.'
                    )

                    # Уведомление абитуриенту
                    Notification.objects.create(
                        user=application.applicant,
                        title=f'Статус заявления №{application.id} обновлен',
                        message=(
                            f'Статус вашего заявления изменен с «{old_status_display}» на «{new_status_display}». '
                            + (f'Комментарий сотрудника: {officer_comment}' if officer_comment else '')
                        ),
                        notification_type=Notification.NotificationType.STATUS_CHANGE,
                        application=application
                    )

                    messages.success(
                        request,
                        f'Статус заявления №{application.id} успешно изменен на «{new_status_display}».'
                    )
                else:
                    messages.error(request, 'Указан некорректный статус или статус не изменился.')

            elif action == 'verify_all_docs':
                updated_count = application.documents.filter(is_verified=False).update(is_verified=True)
                messages.success(
                    request,
                    f'Все документы заявления №{application.id} ({updated_count} шт.) успешно верифицированы.'
                )

            elif action == 'verify_single_doc':
                doc_id = request.POST.get('document_id')
                doc = get_object_or_404(ApplicationDocument, pk=doc_id, application=application)
                doc.is_verified = not doc.is_verified
                doc.save()
                state_label = "верифицирован" if doc.is_verified else "снята верификация"
                messages.success(request, f'Документ «{doc.get_document_type_display()}» {state_label}.')

            return redirect(request.get_full_path())

    # Метрики и сводные KPI
    total_all_applications = Application.objects.count()
    submitted_count = Application.objects.filter(status=Application.Status.SUBMITTED).count()
    under_review_count = Application.objects.filter(status=Application.Status.UNDER_REVIEW).count()
    docs_required_count = Application.objects.filter(status=Application.Status.DOCUMENTS_REQUIRED).count()
    approved_count = Application.objects.filter(status=Application.Status.APPROVED).count()
    enrolled_count = Application.objects.filter(status=Application.Status.ENROLLED).count()
    rejected_count = Application.objects.filter(status=Application.Status.REJECTED).count()
    withdrawn_count = Application.objects.filter(status=Application.Status.WITHDRAWN).count()

    # Заявления, требующие внимания (активная очередь)
    queue_count = submitted_count + under_review_count + docs_required_count

    # Неверифицированные прикрепленные документы
    unverified_docs_count = ApplicationDocument.objects.filter(is_verified=False).count()

    # Заявления за сегодня
    today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    today_submitted_count = Application.objects.filter(submission_date__gte=today_start).count()

    # Фильтры входящей очереди
    status_filter = request.GET.get('status', 'queue')
    faculty_filter = request.GET.get('faculty', '')
    financing_filter = request.GET.get('financing', '')
    search_query = request.GET.get('search', '').strip()
    sort_by = request.GET.get('sort', 'fifo')

    applications = Application.objects.select_related(
        'applicant',
        'applicant__applicant_profile',
        'program',
        'program__specialty',
        'program__specialty__faculty'
    ).prefetch_related(
        'documents',
        'exam_scores',
        'exam_scores__subject'
    )

    # Применение фильтра статуса
    if status_filter == 'queue':
        applications = applications.filter(
            status__in=[
                Application.Status.SUBMITTED,
                Application.Status.UNDER_REVIEW,
                Application.Status.DOCUMENTS_REQUIRED
            ]
        )
    elif status_filter == 'all':
        pass  # все заявления
    elif status_filter in dict(Application.Status.choices):
        applications = applications.filter(status=status_filter)

    # Применение фильтра по факультету
    if faculty_filter:
        applications = applications.filter(program__specialty__faculty_id=faculty_filter)

    # Применение фильтра по форме финансирования
    if financing_filter in dict(Application.FinancingType.choices):
        applications = applications.filter(financing_type=financing_filter)

    # Полнотекстовый / атрибутивный поиск
    if search_query:
        query_parts = search_query.split()
        q_obj = Q()
        for part in query_parts:
            q_obj &= (
                Q(id__icontains=part)
                | Q(applicant__first_name__icontains=part)
                | Q(applicant__last_name__icontains=part)
                | Q(applicant__username__icontains=part)
                | Q(applicant__email__icontains=part)
                | Q(applicant__phone__icontains=part)
                | Q(applicant__applicant_profile__snils__icontains=part)
                | Q(program__specialty__name__icontains=part)
                | Q(program__specialty__code__icontains=part)
            )
        applications = applications.filter(q_obj)

    # Сортировка
    if sort_by == 'newest':
        applications = applications.order_by('-submission_date')
    elif sort_by == 'fifo':
        # Первым поступил — первым обслужен
        applications = applications.order_by('submission_date')
    elif sort_by == 'updated':
        applications = applications.order_by('-updated_at')
    else:
        applications = applications.order_by('submission_date')

    # Пагинация (10 элементов на страницу)
    paginator = Paginator(applications, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Справочники для фильтров
    faculties = Faculty.objects.all().order_by('name')
    financing_choices = Application.FinancingType.choices
    status_choices = Application.Status.choices

    context = {
        'officer_profile': officer_profile,
        'page_obj': page_obj,
        'applications': page_obj.object_list,
        'total_filtered_count': paginator.count,
        # Сводные счетчики
        'metrics': {
            'total_all': total_all_applications,
            'queue': queue_count,
            'submitted': submitted_count,
            'under_review': under_review_count,
            'docs_required': docs_required_count,
            'approved': approved_count,
            'enrolled': enrolled_count,
            'rejected': rejected_count,
            'withdrawn': withdrawn_count,
            'unverified_docs': unverified_docs_count,
            'today_submitted': today_submitted_count,
        },
        # Фильтры
        'status_filter': status_filter,
        'faculty_filter': faculty_filter,
        'financing_filter': financing_filter,
        'search_query': search_query,
        'sort_by': sort_by,
        'faculties': faculties,
        'financing_choices': financing_choices,
        'status_choices': status_choices,
        'developer_name': 'Имя Фамилия',
    }

    return render(request, 'officer/workplace.html', context)


@login_required
@officer_required
def applications_list_view(request):
    """
    Реестр поданных заявлений абитуриентов.
    Обеспечивает полный обзор всех заявлений с фильтрацией по статусам,
    факультетам, форме обучения, основе финансирования, поиском по ФИО,
    контактным данным, СНИЛС и номеру заявления, а также возможность
    быстрого обновления статуса с сохранением аудит-лога.
    """
    user = request.user
    officer_profile = getattr(user, 'officer_profile', None)

    # Обработка POST-действий (быстрое изменение статуса заявления из реестра)
    if request.method == 'POST':
        action = request.POST.get('action')
        application_id = request.POST.get('application_id')

        if application_id:
            application = get_object_or_404(Application, pk=application_id)

            if action == 'change_status':
                new_status = request.POST.get('new_status')
                officer_comment = request.POST.get('officer_comment', '').strip()
                valid_statuses = dict(Application.Status.choices)

                if new_status in valid_statuses and new_status != application.status:
                    old_status = application.status
                    old_status_display = application.get_status_display()
                    application.status = new_status
                    if officer_comment:
                        application.officer_comment = officer_comment
                    application.save()

                    new_status_display = application.get_status_display()

                    # Аудит изменения статуса в истории
                    StatusLog.objects.create(
                        application=application,
                        old_status=old_status,
                        new_status=new_status,
                        changed_by=user,
                        comment=officer_comment or f'Статус изменен сотрудником {user.get_full_name() or user.username} из реестра заявлений.'
                    )

                    # Уведомление абитуриенту
                    Notification.objects.create(
                        user=application.applicant,
                        title=f'Статус заявления №{application.id} обновлен',
                        message=(
                            f'Статус вашего заявления изменен с «{old_status_display}» на «{new_status_display}». '
                            + (f'Комментарий сотрудника: {officer_comment}' if officer_comment else '')
                        ),
                        notification_type=Notification.NotificationType.STATUS_CHANGE,
                        application=application
                    )

                    messages.success(
                        request,
                        f'Статус заявления №{application.id} успешно изменен на «{new_status_display}».'
                    )
                else:
                    messages.error(request, 'Указан некорректный статус или статус не изменился.')

            return redirect(request.get_full_path())

    # Получение параметров фильтрации и поиска
    status_filter = request.GET.get('status', '').strip()
    faculty_filter = request.GET.get('faculty', '').strip()
    financing_filter = request.GET.get('financing', '').strip()
    study_form_filter = request.GET.get('study_form', '').strip()
    search_query = request.GET.get('search', '').strip()
    sort_by = request.GET.get('sort', 'newest').strip()

    # Базовый QuerySet с жадной загрузкой связей для предотвращения N+1
    applications = Application.objects.select_related(
        'applicant',
        'applicant__applicant_profile',
        'program',
        'program__specialty',
        'program__specialty__faculty'
    ).prefetch_related(
        'documents',
        'exam_scores',
        'exam_scores__subject'
    )

    # Фильтрация по статусу
    if status_filter and status_filter in dict(Application.Status.choices):
        applications = applications.filter(status=status_filter)

    # Фильтрация по факультету
    if faculty_filter:
        applications = applications.filter(program__specialty__faculty_id=faculty_filter)

    # Фильтрация по основе обучения (бюджет / договор)
    if financing_filter and financing_filter in dict(Application.FinancingType.choices):
        applications = applications.filter(financing_type=financing_filter)

    # Фильтрация по форме обучения (очная, заочная, очно-заочная)
    if study_form_filter and study_form_filter in dict(EducationProgram.StudyForm.choices):
        applications = applications.filter(program__study_form=study_form_filter)

    # Поиск по ФИО, телефону, email, СНИЛС, номеру заявления или специальности
    if search_query:
        tokens = search_query.split()
        q_expr = Q()
        for token in tokens:
            q_expr &= (
                Q(applicant__first_name__icontains=token)
                | Q(applicant__last_name__icontains=token)
                | Q(applicant__username__icontains=token)
                | Q(applicant__email__icontains=token)
                | Q(applicant__phone__icontains=token)
                | Q(applicant__applicant_profile__snils__icontains=token)
                | Q(id__icontains=token)
                | Q(program__specialty__name__icontains=token)
                | Q(program__specialty__code__icontains=token)
            )
        applications = applications.filter(q_expr)

    # Сортировка записей
    if sort_by == 'oldest':
        applications = applications.order_by('submission_date')
    elif sort_by == 'fio_asc':
        applications = applications.order_by('applicant__last_name', 'applicant__first_name', 'applicant__username')
    elif sort_by == 'fio_desc':
        applications = applications.order_by('-applicant__last_name', '-applicant__first_name', '-applicant__username')
    elif sort_by == 'id_desc':
        applications = applications.order_by('-id')
    elif sort_by == 'id_asc':
        applications = applications.order_by('id')
    elif sort_by == 'status':
        applications = applications.order_by('status', '-submission_date')
    else:  # 'newest' по умолчанию
        applications = applications.order_by('-submission_date')

    # Пагинация (15 заявлений на страницу)
    paginator = Paginator(applications, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Предварительный подсчет документов и баллов для объектов текущей страницы
    for app in page_obj.object_list:
        docs = list(app.documents.all())
        app.docs_total = len(docs)
        app.docs_verified = sum(1 for d in docs if d.is_verified)
        scores = list(app.exam_scores.all())
        app.scores_list = scores
        app.computed_total_score = sum(s.score for s in scores)

    # Сохранение параметров GET-запроса для пагинации (без 'page')
    query_params = request.GET.copy()
    if 'page' in query_params:
        query_params.pop('page')
    pagination_query = query_params.urlencode()

    # Справочники для фильтров
    faculties = Faculty.objects.all().order_by('name')
    financing_choices = Application.FinancingType.choices
    status_choices = Application.Status.choices
    study_form_choices = EducationProgram.StudyForm.choices

    # Сводные счетчики по статусам (для шапки и быстрого переключения)
    status_counts = {
        'total': Application.objects.count(),
        'SUBMITTED': Application.objects.filter(status=Application.Status.SUBMITTED).count(),
        'UNDER_REVIEW': Application.objects.filter(status=Application.Status.UNDER_REVIEW).count(),
        'DOCUMENTS_REQUIRED': Application.objects.filter(status=Application.Status.DOCUMENTS_REQUIRED).count(),
        'APPROVED': Application.objects.filter(status=Application.Status.APPROVED).count(),
        'ENROLLED': Application.objects.filter(status=Application.Status.ENROLLED).count(),
        'REJECTED': Application.objects.filter(status=Application.Status.REJECTED).count(),
        'WITHDRAWN': Application.objects.filter(status=Application.Status.WITHDRAWN).count(),
        'DRAFT': Application.objects.filter(status=Application.Status.DRAFT).count(),
    }

    breadcrumbs = [
        {'title': 'Главная', 'url': '/'},
        {'title': 'Рабочий стол сотрудника', 'url': '/officer/workplace/'},
        {'title': 'Реестр заявлений', 'is_active': True},
    ]

    context = {
        'officer_profile': officer_profile,
        'page_obj': page_obj,
        'applications': page_obj.object_list,
        'total_filtered_count': paginator.count,
        'total_all_count': status_counts['total'],
        'status_counts': status_counts,
        # Активные фильтры
        'status_filter': status_filter,
        'faculty_filter': faculty_filter,
        'financing_filter': financing_filter,
        'study_form_filter': study_form_filter,
        'search_query': search_query,
        'sort_by': sort_by,
        'pagination_query': pagination_query,
        # Справочные данные
        'faculties': faculties,
        'financing_choices': financing_choices,
        'status_choices': status_choices,
        'study_form_choices': study_form_choices,
        'breadcrumbs': breadcrumbs,
    }

    return render(request, 'officer/applications_list.html', context)


@login_required
@officer_required
def application_detail_view(request, pk):
    """
    Детальная карточка проверки заявления абитуриента.
    Позволяет сотруднику приемной комиссии просмотреть все персональные данные,
    выбранную образовательную программу, баллы вступительных испытаний,
    прикрепленные электронные документы с возможностью их предпросмотра,
    а также изменить статус заявления («Принято» / Одобрено, «Отклонено»,
    «Требуются правки» / Требуются документы) с отправкой уведомления и фиксацией в аудит-логе.
    """
    application = get_object_or_404(
        Application.objects.select_related(
            'applicant',
            'applicant__applicant_profile',
            'program',
            'program__specialty',
            'program__specialty__faculty'
        ).prefetch_related(
            'documents',
            'exam_scores',
            'exam_scores__subject',
            'status_logs',
            'status_logs__changed_by'
        ),
        pk=pk
    )

    officer_profile = getattr(request.user, 'officer_profile', None)

    # Обработка действий проверки и изменения статуса
    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'change_status':
            new_status = request.POST.get('new_status')
            officer_comment = request.POST.get('officer_comment', '').strip()
            valid_statuses = dict(Application.Status.choices)

            if new_status in valid_statuses:
                old_status = application.status
                old_status_display = application.get_status_display()
                application.status = new_status
                if officer_comment:
                    application.officer_comment = officer_comment
                application.save()

                new_status_display = application.get_status_display()

                # Аудит изменения статуса
                StatusLog.objects.create(
                    application=application,
                    old_status=old_status,
                    new_status=new_status,
                    changed_by=request.user,
                    comment=officer_comment or f'Статус изменен сотрудником {request.user.get_full_name() or request.user.username} в карточке проверки заявления.'
                )

                # Уведомление абитуриенту
                Notification.objects.create(
                    user=application.applicant,
                    title=f'Статус заявления №{application.id} обновлен',
                    message=(
                        f'Статус вашего заявления изменен на «{new_status_display}». '
                        + (f'Комментарий приемной комиссии: {officer_comment}' if officer_comment else '')
                    ),
                    notification_type=Notification.NotificationType.STATUS_CHANGE,
                    application=application
                )

                messages.success(
                    request,
                    f'Статус заявления №{application.id} успешно изменен на «{new_status_display}».'
                )
                return redirect('officer:application_detail', pk=application.pk)
            else:
                messages.error(request, 'Указан некорректный статус заявления.')

        elif action == 'toggle_doc_verification':
            doc_id = request.POST.get('document_id')
            doc = get_object_or_404(ApplicationDocument, pk=doc_id, application=application)
            doc.is_verified = not doc.is_verified
            doc.save()
            status_text = "подтвержден" if doc.is_verified else "снято подтверждение"
            messages.success(request, f'Документ «{doc.get_document_type_display()}» {status_text}.')
            return redirect('officer:application_detail', pk=application.pk)

        elif action == 'verify_all_docs':
            updated_count = application.documents.filter(is_verified=False).update(is_verified=True)
            messages.success(request, f'Все прикрепленные документы ({updated_count} шт.) успешно подтверждены.')
            return redirect('officer:application_detail', pk=application.pk)

        elif action == 'toggle_score_verification':
            score_id = request.POST.get('score_id')
            score = get_object_or_404(ExamScore, pk=score_id, application=application)
            score.is_verified = not score.is_verified
            score.save()
            status_text = "подтвержден" if score.is_verified else "снято подтверждение"
            messages.success(request, f'Балл по предмету «{score.subject.name}» {status_text}.')
            return redirect('officer:application_detail', pk=application.pk)

    documents = application.documents.all()
    exam_scores = application.exam_scores.all()
    status_logs = application.status_logs.all().order_by('-changed_at')

    # Сводные показатели заявления
    total_docs = documents.count()
    verified_docs = sum(1 for d in documents if d.is_verified)
    total_score = sum(s.score for s in exam_scores)
    all_scores_passing = all(s.is_passing for s in exam_scores) if exam_scores else False

    breadcrumbs = [
        {'title': 'Главная', 'url': '/'},
        {'title': 'Рабочий стол сотрудника', 'url': '/officer/workplace/'},
        {'title': 'Реестр заявлений', 'url': '/officer/applications/'},
        {'title': f'Заявление №{application.id}', 'is_active': True},
    ]

    context = {
        'application': application,
        'applicant': application.applicant,
        'applicant_profile': getattr(application.applicant, 'applicant_profile', None),
        'documents': documents,
        'exam_scores': exam_scores,
        'status_logs': status_logs,
        'total_docs': total_docs,
        'verified_docs': verified_docs,
        'total_score': total_score,
        'all_scores_passing': all_scores_passing,
        'officer_profile': officer_profile,
        'status_choices': Application.Status.choices,
        'breadcrumbs': breadcrumbs,
    }

    return render(request, 'officer/application_detail.html', context)


@login_required
@officer_required
def inquiries_view(request):
    """
    Раздел обработки входящих обращений с формы обратной связи.
    Позволяет сотруднику приемной комиссии просматривать обращения граждан,
    фильтровать их по статусам ('NEW', 'IN_PROGRESS', 'RESOLVED', 'REJECTED'),
    искать по ФИО, email, телефону и теме, а также вводить официальный ответ,
    менять статус и просматривать детали тикета.
    """
    user = request.user
    officer_profile = getattr(user, 'officer_profile', None)

    # Обработка POST-действий (ввод ответа, изменение статуса, взятие в работу)
    if request.method == 'POST':
        action = request.POST.get('action')
        inquiry_id = request.POST.get('inquiry_id')

        if inquiry_id:
            inquiry = get_object_or_404(FeedbackMessage, pk=inquiry_id)

            if action == 'respond':
                response_text = request.POST.get('officer_response', '').strip()
                new_status = request.POST.get('status', FeedbackMessage.Status.RESOLVED)

                if response_text:
                    inquiry.officer_response = response_text
                    inquiry.status = new_status
                    inquiry.responded_by = user
                    inquiry.responded_at = timezone.now()
                    inquiry.save()

                    messages.success(
                        request,
                        f'Ответ на обращение №{inquiry.id} («{inquiry.subject}») успешно сохранен. Статус: «{inquiry.get_status_display()}».'
                    )
                else:
                    messages.error(request, 'Поле ответа сотрудника не может быть пустым.')

            elif action == 'change_status':
                new_status = request.POST.get('status')
                valid_statuses = dict(FeedbackMessage.Status.choices)
                if new_status in valid_statuses:
                    inquiry.status = new_status
                    if not inquiry.responded_by and new_status in [FeedbackMessage.Status.IN_PROGRESS, FeedbackMessage.Status.RESOLVED]:
                        inquiry.responded_by = user
                    inquiry.save()
                    messages.success(
                        request,
                        f'Статус обращения №{inquiry.id} изменен на «{inquiry.get_status_display()}».'
                    )
                else:
                    messages.error(request, 'Указан некорректный статус обращения.')

            elif action == 'take_in_progress':
                inquiry.status = FeedbackMessage.Status.IN_PROGRESS
                inquiry.responded_by = user
                inquiry.save()
                messages.success(
                    request,
                    f'Обращение №{inquiry.id} взято в работу сотрудником {user.get_full_name() or user.username}.'
                )

            return redirect(request.get_full_path())

    # Параметры фильтрации и поиска
    status_filter = request.GET.get('status', '').strip()
    search_query = request.GET.get('search', '').strip()
    sort_by = request.GET.get('sort', 'newest').strip()

    inquiries = FeedbackMessage.objects.select_related('responded_by').all()

    # Фильтр по статусу
    if status_filter and status_filter in dict(FeedbackMessage.Status.choices):
        inquiries = inquiries.filter(status=status_filter)

    # Поиск по ФИО, email, телефону, теме, тексту сообщения
    if search_query:
        tokens = search_query.split()
        q_expr = Q()
        for token in tokens:
            q_expr &= (
                Q(full_name__icontains=token)
                | Q(email__icontains=token)
                | Q(phone__icontains=token)
                | Q(subject__icontains=token)
                | Q(message__icontains=token)
                | Q(id__icontains=token)
            )
        inquiries = inquiries.filter(q_expr)

    # Сортировка
    if sort_by == 'oldest':
        inquiries = inquiries.order_by('created_at')
    elif sort_by == 'name_asc':
        inquiries = inquiries.order_by('full_name')
    elif sort_by == 'name_desc':
        inquiries = inquiries.order_by('-full_name')
    elif sort_by == 'updated':
        inquiries = inquiries.order_by('-updated_at')
    else:  # 'newest' по умолчанию
        inquiries = inquiries.order_by('-created_at')

    # Пагинация (12 обращений на страницу)
    paginator = Paginator(inquiries, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Сохранение параметров GET-запроса для пагинации
    query_params = request.GET.copy()
    if 'page' in query_params:
        query_params.pop('page')
    pagination_query = query_params.urlencode()

    # Сводные счетчики по статусам для верхних табов
    status_counts = {
        'total': FeedbackMessage.objects.count(),
        'NEW': FeedbackMessage.objects.filter(status=FeedbackMessage.Status.NEW).count(),
        'IN_PROGRESS': FeedbackMessage.objects.filter(status=FeedbackMessage.Status.IN_PROGRESS).count(),
        'RESOLVED': FeedbackMessage.objects.filter(status=FeedbackMessage.Status.RESOLVED).count(),
        'REJECTED': FeedbackMessage.objects.filter(status=FeedbackMessage.Status.REJECTED).count(),
    }

    breadcrumbs = [
        {'title': 'Главная', 'url': '/'},
        {'title': 'Рабочий стол сотрудника', 'url': '/officer/workplace/'},
        {'title': 'Обращения граждан', 'is_active': True},
    ]

    context = {
        'officer_profile': officer_profile,
        'page_obj': page_obj,
        'inquiries': page_obj.object_list,
        'total_filtered_count': paginator.count,
        'total_all_count': status_counts['total'],
        'status_counts': status_counts,
        'status_filter': status_filter,
        'search_query': search_query,
        'sort_by': sort_by,
        'pagination_query': pagination_query,
        'status_choices': FeedbackMessage.Status.choices,
        'breadcrumbs': breadcrumbs,
    }

    return render(request, 'officer/inquiries.html', context)


@login_required
@officer_required
def protocols_view(request):
    """
    Страница формирования приказов на зачисление и протоколов приемной комиссии.
    Позволяет сотруднику:
    - Просматривать списки абитуриентов, допущенных к конкурсу (APPROVED) и уже зачисленных (ENROLLED)
    - Фильтровать кандидатов по факультетам, специальностям, формам обучения и основам финансирования
    - Проводить массовое формирование приказов о зачислении с автоматической генерацией аудита и уведомлений
    - Формировать официальные протоколы заседания приемной комиссии с возможностью печати и экспорта
    - Отслеживать заполнение контрольных цифр приема (бюджетных и платных мест)
    """
    user = request.user
    officer_profile = getattr(user, 'officer_profile', None)

    # Обработка POST-действий (формирование приказа / зачисление, отмена зачисления)
    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'generate_order':
            selected_ids = request.POST.getlist('selected_applications')
            order_number = request.POST.get('order_number', '').strip()
            order_date = request.POST.get('order_date', '').strip() or timezone.now().strftime('%d.%m.%Y')
            order_type = request.POST.get('order_type', 'BUDGET')
            order_basis = request.POST.get('order_basis', 'Решение приемной комиссии (протокол заседания)').strip()
            protocol_num = request.POST.get('protocol_number', '').strip() or '1'

            if not selected_ids:
                messages.error(request, 'Не выбрано ни одно заявление для включения в приказ.')
            elif not order_number:
                messages.error(request, 'Пожалуйста, укажите номер формируемого приказа.')
            else:
                apps_to_enroll = Application.objects.filter(
                    id__in=selected_ids,
                    status=Application.Status.APPROVED
                ).select_related('applicant', 'program__specialty')

                enrolled_count = 0
                for app in apps_to_enroll:
                    old_status = app.status
                    app.status = Application.Status.ENROLLED
                    comment_text = (
                        f'Зачислен приказом №{order_number} от {order_date} '
                        f'(Протокол №{protocol_num}). Основание: {order_basis}.'
                    )
                    app.officer_comment = (
                        (app.officer_comment + ' | ' + comment_text) if app.officer_comment else comment_text
                    )
                    app.save()

                    # Фиксация в StatusLog
                    StatusLog.objects.create(
                        application=app,
                        old_status=old_status,
                        new_status=Application.Status.ENROLLED,
                        changed_by=user,
                        comment=f'Включение в приказ о зачислении №{order_number} от {order_date}.'
                    )

                    # Уведомление абитуриенту
                    Notification.objects.create(
                        user=app.applicant,
                        title='Поздравляем! Вы зачислены в МУ им. С.Ю. Витте',
                        message=(
                            f'Уважаемый(ая) {app.applicant.get_full_name() or app.applicant.username}! '
                            f'Вы успешно зачислены на направление «{app.program.specialty.name}» '
                            f'({app.program.get_study_form_display()}, {app.get_financing_type_display()}) '
                            f'приказом №{order_number} от {order_date}.'
                        ),
                        notification_type=Notification.NotificationType.SUCCESS,
                        application=app
                    )
                    enrolled_count += 1

                if enrolled_count > 0:
                    messages.success(
                        request,
                        f'Приказ №{order_number} от {order_date} успешно сформирован. '
                        f'Зачислено абитуриентов: {enrolled_count} чел.'
                    )
                else:
                    messages.warning(
                        request,
                        'Среди выбранных заявлений не найдено заявлений со статусом «Одобрено».'
                    )

            return redirect(request.get_full_path())

        elif action == 'revert_enrollment':
            application_id = request.POST.get('application_id')
            revert_reason = request.POST.get('revert_reason', '').strip()
            if application_id:
                app = get_object_or_404(Application, pk=application_id)
                if app.status == Application.Status.ENROLLED:
                    app.status = Application.Status.APPROVED
                    comment_text = f'Исключен из приказа: {revert_reason or "По решению приемной комиссии"}'
                    app.officer_comment = (
                        (app.officer_comment + ' | ' + comment_text) if app.officer_comment else comment_text
                    )
                    app.save()

                    StatusLog.objects.create(
                        application=app,
                        old_status=Application.Status.ENROLLED,
                        new_status=Application.Status.APPROVED,
                        changed_by=user,
                        comment=f'Исключение из приказа о зачислении. {revert_reason}'
                    )

                    Notification.objects.create(
                        user=app.applicant,
                        title=f'Статус заявления №{app.id} изменен',
                        message=(
                            f'Ваше заявление переведено обратно в статус «Одобрено (допущен к конкурсу)». '
                            f'Причина: {revert_reason or "Корректировка состава приказа"}.'
                        ),
                        notification_type=Notification.NotificationType.STATUS_CHANGE,
                        application=app
                    )

                    messages.success(
                        request,
                        f'Заявление №{app.id} ({app.applicant.get_full_name() or app.applicant.username}) возвращено в статус «Одобрено».'
                    )
            return redirect(request.get_full_path())

    # Параметры фильтрации
    status_filter = request.GET.get('status', 'APPROVED')  # 'APPROVED', 'ENROLLED', 'ALL_ELIGIBLE'
    faculty_id = request.GET.get('faculty', '').strip()
    specialty_id = request.GET.get('specialty', '').strip()
    study_form = request.GET.get('study_form', '').strip()
    financing_type = request.GET.get('financing', '').strip()
    search_query = request.GET.get('search', '').strip()
    sort_by = request.GET.get('sort', 'score_desc').strip()

    # Базовая выборка заявлений (APPROVED или ENROLLED)
    eligible_statuses = [Application.Status.APPROVED, Application.Status.ENROLLED]
    applications_qs = Application.objects.filter(
        status__in=eligible_statuses
    ).select_related(
        'applicant',
        'applicant__applicant_profile',
        'program',
        'program__specialty',
        'program__specialty__faculty'
    ).prefetch_related(
        'documents',
        'exam_scores',
        'exam_scores__subject'
    )

    if status_filter == 'APPROVED':
        applications_qs = applications_qs.filter(status=Application.Status.APPROVED)
    elif status_filter == 'ENROLLED':
        applications_qs = applications_qs.filter(status=Application.Status.ENROLLED)

    if faculty_id:
        applications_qs = applications_qs.filter(program__specialty__faculty_id=faculty_id)

    if specialty_id:
        applications_qs = applications_qs.filter(program__specialty_id=specialty_id)

    if study_form:
        applications_qs = applications_qs.filter(program__study_form=study_form)

    if financing_type:
        applications_qs = applications_qs.filter(financing_type=financing_type)

    if search_query:
        tokens = search_query.split()
        q_expr = Q()
        for token in tokens:
            q_expr &= (
                Q(applicant__first_name__icontains=token)
                | Q(applicant__last_name__icontains=token)
                | Q(applicant__username__icontains=token)
                | Q(applicant__applicant_profile__snils__icontains=token)
                | Q(id__icontains=token)
                | Q(program__specialty__name__icontains=token)
                | Q(program__specialty__code__icontains=token)
            )
        applications_qs = applications_qs.filter(q_expr)

    # Добавляем сортировку по баллам или дате
    apps_list = list(applications_qs)
    if sort_by == 'score_desc':
        apps_list.sort(key=lambda a: a.total_score, reverse=True)
    elif sort_by == 'score_asc':
        apps_list.sort(key=lambda a: a.total_score)
    elif sort_by == 'name_asc':
        apps_list.sort(key=lambda a: a.applicant.get_full_name() or a.applicant.username)
    elif sort_by == 'date_desc':
        apps_list.sort(key=lambda a: a.submission_date, reverse=True)
    else:
        apps_list.sort(key=lambda a: a.total_score, reverse=True)

    # Подсчет сводной статистики для плашек
    total_approved = Application.objects.filter(status=Application.Status.APPROVED).count()
    total_enrolled = Application.objects.filter(status=Application.Status.ENROLLED).count()
    total_budget_enrolled = Application.objects.filter(
        status=Application.Status.ENROLLED,
        financing_type=Application.FinancingType.BUDGET
    ).count()
    total_paid_enrolled = Application.objects.filter(
        status=Application.Status.ENROLLED,
        financing_type=Application.FinancingType.PAID
    ).count()

    total_budget_places = Specialty.objects.filter(is_active=True).aggregate(Sum('budget_places'))['budget_places__sum'] or 0
    total_paid_places = Specialty.objects.filter(is_active=True).aggregate(Sum('paid_places'))['paid_places__sum'] or 0

    # Справочники для фильтрации
    faculties = Faculty.objects.all().order_by('name')
    specialties = Specialty.objects.filter(is_active=True).select_related('faculty').order_by('name')
    study_forms = EducationProgram.StudyForm.choices
    financing_choices = Application.FinancingType.choices

    # Группировка по направлениям для сводки плана приема
    specialty_stats = []
    for spec in specialties:
        spec_approved = Application.objects.filter(program__specialty=spec, status=Application.Status.APPROVED).count()
        spec_enrolled_budget = Application.objects.filter(
            program__specialty=spec,
            status=Application.Status.ENROLLED,
            financing_type=Application.FinancingType.BUDGET
        ).count()
        spec_enrolled_paid = Application.objects.filter(
            program__specialty=spec,
            status=Application.Status.ENROLLED,
            financing_type=Application.FinancingType.PAID
        ).count()

        specialty_stats.append({
            'specialty': spec,
            'approved_count': spec_approved,
            'budget_places': spec.budget_places,
            'enrolled_budget': spec_enrolled_budget,
            'budget_remaining': max(0, spec.budget_places - spec_enrolled_budget),
            'paid_places': spec.paid_places,
            'enrolled_paid': spec_enrolled_paid,
            'paid_remaining': max(0, spec.paid_places - spec_enrolled_paid),
        })

    breadcrumbs = [
        {'title': 'Главная', 'url': '/'},
        {'title': 'Рабочий стол сотрудника', 'url': '/officer/workplace/'},
        {'title': 'Приказы и протоколы зачисления', 'is_active': True},
    ]

    context = {
        'officer_profile': officer_profile,
        'applications': apps_list,
        'total_count': len(apps_list),
        'metrics': {
            'total_approved': total_approved,
            'total_enrolled': total_enrolled,
            'total_budget_enrolled': total_budget_enrolled,
            'total_paid_enrolled': total_paid_enrolled,
            'total_budget_places': total_budget_places,
            'total_paid_places': total_paid_places,
            'budget_fill_percentage': round((total_budget_enrolled / total_budget_places * 100) if total_budget_places else 0, 1),
            'paid_fill_percentage': round((total_paid_enrolled / total_paid_places * 100) if total_paid_places else 0, 1),
        },
        'specialty_stats': specialty_stats,
        'faculties': faculties,
        'specialties': specialties,
        'study_forms': study_forms,
        'financing_choices': financing_choices,
        'status_filter': status_filter,
        'faculty_id': faculty_id,
        'specialty_id': specialty_id,
        'study_form': study_form,
        'financing_type': financing_type,
        'search_query': search_query,
        'sort_by': sort_by,
        'breadcrumbs': breadcrumbs,
        'current_date': timezone.now().strftime('%d.%m.%Y'),
        'current_year': timezone.now().year,
    }

    return render(request, 'officer/protocols.html', context)




