from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Count, Sum
from django.core.paginator import Paginator
from django.utils import timezone

from .decorators import officer_required
from admissions.models import Application, ApplicationDocument, Faculty, EducationProgram
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
