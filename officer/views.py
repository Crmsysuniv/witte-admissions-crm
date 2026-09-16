from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Count, Sum
from django.core.paginator import Paginator
from django.utils import timezone

from .decorators import officer_required
from admissions.models import Application, ApplicationDocument, Faculty, EducationProgram, ExamScore
from audit.models import StatusLog, Notification
from accounts.models import OfficerProfile


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


