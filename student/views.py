from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from accounts.models import ApplicantProfile
from admissions.models import Application, ApplicationDocument, ExamScore, Specialty, EducationProgram
from audit.models import Notification


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
        },
        {
            'num': 2,
            'title': 'Анкета абитуриента',
            'desc': 'Паспортные данные и СНИЛС',
            'completed': step2_profile,
            'current': step1_account and not step2_profile,
            'icon': 'bi-card-text',
        },
        {
            'num': 3,
            'title': 'Подача заявления',
            'desc': 'Выбор программ обучения',
            'completed': step3_application,
            'current': step2_profile and not step3_application,
            'icon': 'bi-file-earmark-plus-fill',
        },
        {
            'num': 4,
            'title': 'Загрузка документов',
            'desc': 'Скан паспорта и аттестата',
            'completed': step4_documents,
            'current': step3_application and not step4_documents,
            'icon': 'bi-folder-check',
        },
        {
            'num': 5,
            'title': 'Баллы ЕГЭ / ВИ',
            'desc': 'Внесение результатов экзаменов',
            'completed': step5_scores,
            'current': step4_documents and not step5_scores,
            'icon': 'bi-award-fill',
        },
        {
            'num': 6,
            'title': 'Допуск к конкурсу',
            'desc': 'Приказ о зачислении',
            'completed': step6_approval,
            'current': step5_scores and not step6_approval,
            'icon': 'bi-patch-check-fill',
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
            'title': 'Каталог программ 2026',
            'desc': 'Специальности бакалавриата, специалитета и колледжа',
            'url': '/programs/',
            'icon': 'bi-journal-bookmark-fill',
            'color': 'indigo',
        },
        {
            'title': 'Калькулятор баллов ЕГЭ',
            'desc': 'Проверьте шансы на бюджет и платное обучение',
            'url': '/calculator/',
            'icon': 'bi-calculator-fill',
            'color': 'blue',
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
            'color': 'cyan',
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
