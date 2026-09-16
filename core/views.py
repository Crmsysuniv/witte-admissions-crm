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


def faq(request):
    """
    Страница «Часто задаваемые вопросы (FAQ)» МУ им. С.Ю. Витте.
    """
    faq_categories = [
        {
            'id': 'documents',
            'name': 'Подача документов и сроки',
            'icon': 'bi-folder-check',
            'color': 'blue',
            'questions': [
                {
                    'q': 'Какие документы обязательны при первичной подаче заявления?',
                    'a': 'Для первичной подачи заявления через онлайн-портал CRM или лично в приемной комиссии понадобятся: 1) Паспорт гражданина РФ (разворот с фото и страница с регистрацией); 2) Документ об образовании установленного образца (аттестат за 11 классов или диплом колледжа/техникума с приложением); 3) Страховое свидетельство СНИЛС (обязательно для внесения в единую федеральную систему ФИС ГИА и Приема); 4) Документы, подтверждающие индивидуальные достижения (значок ГТО, аттестат с отличием, победы в олимпиадах); 5) Документы, подтверждающие особые права или квоты (при наличии).',
                },
                {
                    'q': 'Каковы сроки приема документов в 2026 году?',
                    'a': 'Прием документов на программы бакалавриата и специалитета стартует 20 июня 2026 года. Для поступающих по результатам внутренних вступительных испытаний прием завершается 10 июля 2026 года. Для поступающих только по результатам ЕГЭ на бюджетные места — 25 июля 2026 года. На места по договорам об оказании платных образовательных услуг прием документов продолжается до 28 августа 2026 года (на заочную форму — до 25 октября 2026 года).',
                },
                {
                    'q': 'Можно ли подать заявление, если результаты ЕГЭ еще не опубликованы?',
                    'a': 'Да, безусловно! Вы можете подать электронное заявление в CRM-системе уже сейчас, не дожидаясь публикации всех результатов экзаменов. Укажите сдаваемые предметы, а баллы автоматически подгрузятся из Федеральной информационной системы (ФИС ГИА) сразу после их официальной проверки Рособрнадзором.',
                },
                {
                    'q': 'В скольких направлениях подготовки можно участвовать одновременно?',
                    'a': 'В соответствии с Порядком приема Минобрнауки РФ, в Московском университете имени С.Ю. Витте абитуриент может одновременно подать заявление на 5 направлений подготовки (специальностей). В рамках каждого направления вы вправе выбрать различные формы обучения (очную, очно-заочную, заочную) и условия финансирования (бюджет и платная основа).',
                },
            ]
        },
        {
            'id': 'exams',
            'name': 'ЕГЭ и вступительные испытания',
            'icon': 'bi-card-checklist',
            'color': 'indigo',
            'questions': [
                {
                    'q': 'Кто имеет право сдавать внутренние вступительные испытания вместо ЕГЭ?',
                    'a': 'Сдавать вступительные испытания, проводимые университетом самостоятельно (компьютерное тестирование), имеют право: 1) Выпускники колледжей, техникумов и училищ (с дипломом о среднем профессиональном образовании); 2) Лица, уже имеющие высшее образование (для получения второго высшего); 3) Инвалиды и дети-инвалиды; 4) Иностранные граждане; 5) Граждане РФ, получившие документ о среднем общем образовании в иностранных образовательных организациях в текущем году.',
                },
                {
                    'q': 'Сколько действуют результаты ЕГЭ для поступления в 2026 году?',
                    'a': 'В 2026 году действительны результаты Единого государственного экзамена, сданные в 2022, 2023, 2024, 2025 и 2026 годах (срок действия — 4 года, следующих за годом сдачи экзамена, согласно ст. 70 ФЗ № 273).',
                },
                {
                    'q': 'Как учитываются индивидуальные достижения (ГТО, золотая медаль, олимпиады)?',
                    'a': 'За индивидуальные достижения абитуриенту начисляются дополнительные конкурсные баллы, которые суммируются с баллами ЕГЭ (но не более 10 баллов суммарно): аттестат с золотой/серебряной медалью или диплом СПО с отличием (+5 баллов); золотой или серебряный значок ГТО (+2 балла); волонтерская книжка DOBRO.RU от 100 часов (+2 балла); победители и призеры профильных олимпиад (+5 баллов).',
                },
                {
                    'q': 'Что делать, если по одному из предметов балл ниже минимального порога?',
                    'a': 'Если балл ЕГЭ ниже минимального порогового значения, установленного университетом для допуска к конкурсу, данный результат не может быть принят. Однако во многих направлениях подготовки МУ им. С.Ю. Витте предусмотрен предмет по выбору абитуриента (например, физика или информатика на IT-факультете; история или обществознание на юриспруденции), что позволяет заменить дисциплину на сданную более успешно.',
                },
            ]
        },
        {
            'id': 'fees',
            'name': 'Стоимость, скидки и кредит 3%',
            'icon': 'bi-tag-fill',
            'color': 'emerald',
            'questions': [
                {
                    'q': 'Фиксируется ли стоимость обучения в договоре?',
                    'a': 'Да, полная стоимость образовательных услуг на весь период обучения четко фиксируется в двустороннем или трехстороннем договоре при поступлении. Возможно лишь ежегодное изменение стоимости исключительно на официальный уровень инфляции, предусмотренный федеральным законом о бюджете РФ (ст. 54 ФЗ «Об образовании в РФ»).',
                },
                {
                    'q': 'Как получить скидку на обучение до 20%?',
                    'a': 'Университет предоставляет гибкую систему скидок: при сумме баллов ЕГЭ 240+ — скидка 20%; от 200 до 239 баллов — 15%; от 180 до 199 баллов — 10%. Выпускникам собственного Колледжа Витте гарантирована скидка 15% на весь период бакалавриата. Также действует скидка 20% для участников СВО и их детей и семейная скидка 10%.',
                },
                {
                    'q': 'Как работает образовательный кредит с господдержкой по ставке 3%?',
                    'a': 'Это федеральная государственная программа поддержки студентов от Сбербанка и Минобрнауки РФ. Ставка для студента составляет всего 3% годовых (остальную процентную ставку банку компенсирует государство). Во время всей учебы студент платит только минимальные начисленные проценты (от 200 до 800 рублей в месяц), а основной долг начинает гаситься только через 9 месяцев после окончания университета в течение 15 лет.',
                },
                {
                    'q': 'Можно ли оплатить обучение материнским капиталом или в рассрочку?',
                    'a': 'Да! Университет принимает к оплате как федеральный, так и региональный материнский капитал. Специалисты приемной комиссии бесплатно формируют полный пакет документов для Социального фонда РФ. Кроме того, действует внутренняя рассрочка от университета без участия банков на 10 равных платежей в течение года под 0%.',
                },
            ]
        },
        {
            'id': 'dormitory',
            'name': 'Общежитие и студенческая жизнь',
            'icon': 'bi-houses-fill',
            'color': 'amber',
            'questions': [
                {
                    'q': 'Гарантируется ли общежитие иногородним студентам?',
                    'a': 'Да, Московский университет имени С.Ю. Витте гарантирует 100% предоставление мест в общежитиях всем иногородним студентам 1 курса очной формы обучения. Жилой фонд включает 3 современных корпуса блочного и квартирного типа (от 6 500 рублей в месяц).',
                },
                {
                    'q': 'Где расположены общежития и сколько времени занимает дорога до вуза?',
                    'a': 'Основной студенческий комплекс «Автозаводский» расположен всего в 3 минутах пешком от главного учебного кампуса университета (ЮАО Москвы, 2-й Кожуховский проезд). Корпус «Нагатинский» расположен в 10 минутах езды на метро, а партнерский комплекс «Дубровка» — в 15 минутах.',
                },
                {
                    'q': 'Какие условия созданы в общежитиях университета?',
                    'a': 'Все комнаты укомплектованы удобной мебелью (кровати с ортопедическими матрасами, письменные столы, гардеробные шкафы). В корпусах действуют кухни с индукционными плитами, бесплатные прачечные самообслуживания со стиральными и сушильными машинами, коворкинги с Wi-Fi 200 Мбит/с, тренажерные залы и круглосуточная охрана с системой контроля доступа СКУД.',
                },
            ]
        },
        {
            'id': 'transfer',
            'name': 'Перевод и восстановление',
            'icon': 'bi-arrow-left-right',
            'color': 'purple',
            'questions': [
                {
                    'q': 'Как перевестись в МУ им. С.Ю. Витте из другого университета?',
                    'a': 'Перевод возможен из любого вуза РФ, имеющего государственную аккредитацию, в течение всего учебного года. Для перевода необходимо: 1) Заказать справку о периоде обучения (с перечнем сданных дисциплин и часов) в вашем текущем вузе; 2) Отправить скан справки в деканат Витте для составления академической справки о перезачете; 3) Получить справку-согласие на перевод и оформить приказ о зачислении без потери курса.',
                },
                {
                    'q': 'Сохраняется ли отсрочка от армии при переводе?',
                    'a': 'Да, при переводе из одного аккредитованного вуза в другой на программу того же уровня образования (например, с бакалавриата на бакалавриат очной формы) отсрочка от призыва на военную службу сохраняется в полном объеме при условии, что общий срок обучения увеличивается не более чем на один год (ст. 24 ФЗ «О воинской обязанности и военной службе»).',
                },
            ]
        },
    ]

    total_questions = sum(len(c['questions']) for c in faq_categories)

    context = {
        'faq_categories': faq_categories,
        'total_questions': total_questions,
    }
    return render(request, 'faq.html', context)


def contacts(request):
    """
    Страница «Контакты приемной комиссии и схема проезда» МУ им. С.Ю. Витте.
    """
    branches = [
        {
            'city': 'г. Рязань',
            'name': 'Рязанский филиал МУ им. С.Ю. Витте',
            'address': '390013, г. Рязань, Первомайский проспект, д. 62',
            'phone': '+7 (4912) 98-44-55',
            'email': 'ryazan@witte.ru',
            'metro_desc': 'Остановка «Площадь Ленина»',
        },
        {
            'city': 'г. Пенза',
            'name': 'Пензенский филиал МУ им. С.Ю. Витте',
            'address': '440011, г. Пенза, ул. Вяземского, д. 25Б',
            'phone': '+7 (8412) 49-65-81',
            'email': 'penza@witte.ru',
            'metro_desc': 'Остановка «Улица Леонова»',
        },
        {
            'city': 'г. Ростов-на-Дону',
            'name': 'Ростовский филиал МУ им. С.Ю. Витте',
            'address': '344002, г. Ростов-на-Дону, ул. Ленина, д. 44',
            'phone': '+7 (863) 244-12-85',
            'email': 'rostov@witte.ru',
            'metro_desc': 'Остановка «Проспект Ворошиловский»',
        },
        {
            'city': 'г. Сергиев Посад',
            'name': 'Сергиево-Посадский филиал МУ им. С.Ю. Витте',
            'address': '141300, Московская обл., г. Сергиев Посад, Московское шоссе, д. 22А',
            'phone': '+7 (496) 547-44-11',
            'email': 'sposad@witte.ru',
            'metro_desc': '5 минут от ж/д станции Сергиев Посад',
        },
    ]

    context = {
        'branches': branches,
    }
    return render(request, 'contacts.html', context)


from datetime import timedelta
import json
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import Count, Sum, Avg, Q, F
from django.utils import timezone
from accounts.decorators import admin_required
from accounts.models import User, ApplicantProfile, OfficerProfile
from admissions.models import Faculty, Specialty, EducationProgram, ExamSubject, Application, ApplicationDocument, ExamScore
from audit.models import StatusLog, Notification
from feedback.models import FeedbackMessage


@admin_required
def admin_dashboard_view(request):
    """
    Главный аналитический дашборд руководителя / администратора CRM (admin/dashboard.html).
    Отображает исчерпывающий комплекс управленческих метрик, KPI приемной кампании,
    анализ распределения бюджетных и платных мест, воронку конверсии от регистрации до зачисления,
    финансовые прогнозы, нагрузку на комиссию и интерактивную инфографику.
    """
    now = timezone.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=7)
    month_start = today_start - timedelta(days=30)

    # 1. Основные объемы заявлений и динамика
    total_applications = Application.objects.count()
    today_applications = Application.objects.filter(submission_date__gte=today_start).count()
    week_applications = Application.objects.filter(submission_date__gte=week_start).count()
    month_applications = Application.objects.filter(submission_date__gte=month_start).count()

    submitted_count = Application.objects.filter(status=Application.Status.SUBMITTED).count()
    under_review_count = Application.objects.filter(status=Application.Status.UNDER_REVIEW).count()
    docs_required_count = Application.objects.filter(status=Application.Status.DOCUMENTS_REQUIRED).count()
    approved_count = Application.objects.filter(status=Application.Status.APPROVED).count()
    enrolled_count = Application.objects.filter(status=Application.Status.ENROLLED).count()
    rejected_count = Application.objects.filter(status=Application.Status.REJECTED).count()
    withdrawn_count = Application.objects.filter(status=Application.Status.WITHDRAWN).count()
    draft_count = Application.objects.filter(status=Application.Status.DRAFT).count()

    queue_count = submitted_count + under_review_count + docs_required_count

    # 2. Бюджет vs Платное обучение (План / Факт / Конкурс)
    total_budget_places = Specialty.objects.filter(is_active=True).aggregate(Sum('budget_places'))['budget_places__sum'] or 0
    total_paid_places = Specialty.objects.filter(is_active=True).aggregate(Sum('paid_places'))['paid_places__sum'] or 0
    total_planned_places = total_budget_places + total_paid_places

    budget_apps_count = Application.objects.filter(financing_type=Application.FinancingType.BUDGET).count()
    budget_approved_count = Application.objects.filter(financing_type=Application.FinancingType.BUDGET, status=Application.Status.APPROVED).count()
    budget_enrolled_count = Application.objects.filter(financing_type=Application.FinancingType.BUDGET, status=Application.Status.ENROLLED).count()

    paid_apps_count = Application.objects.filter(financing_type=Application.FinancingType.PAID).count()
    paid_approved_count = Application.objects.filter(financing_type=Application.FinancingType.PAID, status=Application.Status.APPROVED).count()
    paid_enrolled_count = Application.objects.filter(financing_type=Application.FinancingType.PAID, status=Application.Status.ENROLLED).count()

    total_enrolled_all = budget_enrolled_count + paid_enrolled_count

    budget_fill_rate = round((budget_enrolled_count / total_budget_places * 100) if total_budget_places else 0, 1)
    paid_fill_rate = round((paid_enrolled_count / total_paid_places * 100) if total_paid_places else 0, 1)
    overall_fill_rate = round((total_enrolled_all / total_planned_places * 100) if total_planned_places else 0, 1)

    budget_competition = round((budget_apps_count / total_budget_places) if total_budget_places else 0, 2)
    paid_competition = round((paid_apps_count / total_paid_places) if total_paid_places else 0, 2)
    overall_competition = round((total_applications / total_planned_places) if total_planned_places else 0, 2)

    budget_share = round((budget_apps_count / total_applications * 100) if total_applications else 0, 1)
    paid_share = round((paid_apps_count / total_applications * 100) if total_applications else 0, 1)

    # 3. Воронка конверсии (Conversion Funnel)
    stage_registered = User.objects.filter(role=User.Role.APPLICANT).count()
    stage_applied = Application.objects.values('applicant_id').distinct().count()
    stage_with_docs = ApplicationDocument.objects.values('application__applicant_id').distinct().count()
    stage_approved = Application.objects.filter(
        status__in=[Application.Status.APPROVED, Application.Status.ENROLLED]
    ).values('applicant_id').distinct().count()
    stage_enrolled = Application.objects.filter(status=Application.Status.ENROLLED).values('applicant_id').distinct().count()

    conv_reg_to_app = round((stage_applied / stage_registered * 100) if stage_registered else 0, 1)
    conv_app_to_docs = round((stage_with_docs / stage_applied * 100) if stage_applied else 0, 1)
    conv_docs_to_appr = round((stage_approved / stage_with_docs * 100) if stage_with_docs else 0, 1)
    conv_appr_to_enr = round((stage_enrolled / stage_approved * 100) if stage_approved else 0, 1)
    overall_conversion = round((stage_enrolled / stage_registered * 100) if stage_registered else 0, 1)

    # 4. Финансовые метрики
    enrolled_paid_revenue = Application.objects.filter(
        status=Application.Status.ENROLLED,
        financing_type=Application.FinancingType.PAID
    ).aggregate(total=Sum('program__tuition_fee'))['total'] or 0

    pipeline_paid_revenue = Application.objects.filter(
        status__in=[Application.Status.APPROVED, Application.Status.ENROLLED],
        financing_type=Application.FinancingType.PAID
    ).aggregate(total=Sum('program__tuition_fee'))['total'] or 0

    avg_annual_tuition = EducationProgram.objects.filter(is_active=True).aggregate(avg=Avg('tuition_fee'))['avg'] or 0

    # 5. Подтвержденные документы об образовании (аттестаты/дипломы) и средние баллы
    verified_edu_docs_count = ApplicationDocument.objects.filter(
        document_type__in=[ApplicationDocument.DocumentType.CERTIFICATE, ApplicationDocument.DocumentType.DIPLOMA],
        is_verified=True
    ).values('application_id').distinct().count()
    verified_edu_percentage = round((verified_edu_docs_count / total_applications * 100) if total_applications else 0, 1)

    all_apps = Application.objects.prefetch_related('exam_scores').all()
    all_scores = []
    budget_scores = []
    paid_scores = []
    for app in all_apps:
        score = app.total_score
        if score > 0:
            all_scores.append(score)
            if app.financing_type == Application.FinancingType.BUDGET:
                budget_scores.append(score)
            else:
                paid_scores.append(score)

    avg_total_score = round(sum(all_scores) / len(all_scores), 1) if all_scores else 0
    avg_budget_score = round(sum(budget_scores) / len(budget_scores), 1) if budget_scores else 0
    avg_paid_score = round(sum(paid_scores) / len(paid_scores), 1) if paid_scores else 0

    # 6. Операционные показатели
    total_users_count = User.objects.count()
    total_officers_count = User.objects.filter(role=User.Role.OFFICER).count()
    unverified_docs_count = ApplicationDocument.objects.filter(is_verified=False).count()
    total_docs_count = ApplicationDocument.objects.count()
    verified_docs_percent = round(((total_docs_count - unverified_docs_count) / total_docs_count * 100) if total_docs_count else 0, 1)

    new_feedback_count = FeedbackMessage.objects.filter(status=FeedbackMessage.Status.NEW).count()
    in_progress_feedback_count = FeedbackMessage.objects.filter(status=FeedbackMessage.Status.IN_PROGRESS).count()
    total_feedback_count = FeedbackMessage.objects.count()

    # 7. Аналитика по институтам и факультетам
    faculties = Faculty.objects.prefetch_related('specialties__programs').all().order_by('name')
    faculty_stats = []
    faculty_chart_labels = []
    faculty_chart_data = []

    for fac in faculties:
        f_specs = fac.specialties.filter(is_active=True)
        f_b_places = f_specs.aggregate(total=Sum('budget_places'))['total'] or 0
        f_p_places = f_specs.aggregate(total=Sum('paid_places'))['total'] or 0
        f_tot_places = f_b_places + f_p_places

        f_apps = Application.objects.filter(program__specialty__faculty=fac)
        f_apps_tot = f_apps.count()
        f_apps_b = f_apps.filter(financing_type=Application.FinancingType.BUDGET).count()
        f_apps_p = f_apps.filter(financing_type=Application.FinancingType.PAID).count()

        f_enr_b = f_apps.filter(status=Application.Status.ENROLLED, financing_type=Application.FinancingType.BUDGET).count()
        f_enr_p = f_apps.filter(status=Application.Status.ENROLLED, financing_type=Application.FinancingType.PAID).count()
        f_enr_tot = f_enr_b + f_enr_p

        f_fill = round((f_enr_tot / f_tot_places * 100) if f_tot_places else 0, 1)
        f_comp = round((f_apps_tot / f_tot_places) if f_tot_places else 0, 2)
        f_conv = round((f_enr_tot / f_apps_tot * 100) if f_apps_tot else 0, 1)

        faculty_stats.append({
            'faculty': fac,
            'specialties_count': f_specs.count(),
            'budget_places': f_b_places,
            'paid_places': f_p_places,
            'total_places': f_tot_places,
            'apps_total': f_apps_tot,
            'apps_budget': f_apps_b,
            'apps_paid': f_apps_p,
            'enrolled_total': f_enr_tot,
            'enrolled_budget': f_enr_b,
            'enrolled_paid': f_enr_p,
            'fill_rate': f_fill,
            'competition': f_comp,
            'conversion': f_conv,
        })

        faculty_chart_labels.append(fac.code or fac.name)
        faculty_chart_data.append(f_apps_tot)

    # 8. Топ популярных направлений подготовки
    top_specialties_qs = Specialty.objects.filter(is_active=True).annotate(
        apps_count=Count('programs__applications')
    ).select_related('faculty').order_by('-apps_count')[:6]

    top_specialties = []
    max_spec_apps = max([s.apps_count for s in top_specialties_qs] or [1])
    for sp in top_specialties_qs:
        sp_tot_places = sp.budget_places + sp.paid_places
        sp_enrolled = Application.objects.filter(program__specialty=sp, status=Application.Status.ENROLLED).count()
        top_specialties.append({
            'specialty': sp,
            'apps_count': sp.apps_count,
            'percent_of_max': round((sp.apps_count / max_spec_apps * 100) if max_spec_apps else 0, 1),
            'budget_places': sp.budget_places,
            'paid_places': sp.paid_places,
            'total_places': sp_tot_places,
            'enrolled_count': sp_enrolled,
            'competition': round((sp.apps_count / sp_tot_places) if sp_tot_places else 0, 2),
        })

    # 9. Распределение по формам обучения
    study_forms_stat = []
    for form_code, form_name in EducationProgram.StudyForm.choices:
        f_count = Application.objects.filter(program__study_form=form_code).count()
        f_pct = round((f_count / total_applications * 100) if total_applications else 0, 1)
        study_forms_stat.append({
            'code': form_code,
            'name': form_name,
            'count': f_count,
            'percentage': f_pct,
        })

    # 10. График динамики за последние 14 дней
    chart_dates = []
    chart_submitted_counts = []
    chart_enrolled_counts = []
    for i in range(13, -1, -1):
        day_date = (now - timedelta(days=i)).date()
        day_start = timezone.make_aware(timezone.datetime.combine(day_date, timezone.datetime.min.time()))
        day_end = timezone.make_aware(timezone.datetime.combine(day_date, timezone.datetime.max.time()))

        sub_c = Application.objects.filter(submission_date__range=(day_start, day_end)).count()
        enr_c = StatusLog.objects.filter(new_status=Application.Status.ENROLLED, changed_at__range=(day_start, day_end)).count()

        chart_dates.append(day_date.strftime('%d.%m'))
        chart_submitted_counts.append(sub_c)
        chart_enrolled_counts.append(enr_c)

    # 11. Лента последних операций аудита (StatusLog)
    recent_logs = StatusLog.objects.select_related(
        'application',
        'application__applicant',
        'application__program__specialty',
        'changed_by'
    ).order_by('-changed_at')[:8]

    # Данные для JS-графиков в формате JSON
    charts_json = {
        'timeline_dates': chart_dates,
        'timeline_submitted': chart_submitted_counts,
        'timeline_enrolled': chart_enrolled_counts,
        'faculty_labels': faculty_chart_labels,
        'faculty_data': faculty_chart_data,
        'faculty_bar': {
            'labels': [fac.name for fac in faculties],
            'short_labels': faculty_chart_labels,
            'total': [f['apps_total'] for f in faculty_stats],
            'budget': [f['apps_budget'] for f in faculty_stats],
            'paid': [f['apps_paid'] for f in faculty_stats],
            'enrolled': [f['enrolled_total'] for f in faculty_stats],
            'places': [f['total_places'] for f in faculty_stats],
        },
        'study_forms_pie': {
            'labels': [f['name'] for f in study_forms_stat],
            'data': [f['count'] for f in study_forms_stat],
            'percentages': [f['percentage'] for f in study_forms_stat],
            'codes': [f['code'] for f in study_forms_stat],
        },
        'funnel_labels': ['Регистрации', 'Подали заявление', 'Загрузили документы', 'Одобрены (конкурс)', 'Зачислены'],
        'funnel_data': [stage_registered, stage_applied, stage_with_docs, stage_approved, stage_enrolled],
        'budget_paid_comparison': {
            'budget_places': total_budget_places,
            'budget_enrolled': budget_enrolled_count,
            'paid_places': total_paid_places,
            'paid_enrolled': paid_enrolled_count,
        }
    }

    breadcrumbs = [
        {'title': 'Главная', 'url': '/'},
        {'title': 'Панель администратора', 'url': '/admin/'},
        {'title': 'Аналитический дашборд руководителя', 'is_active': True},
    ]

    context = {
        'total_applications': total_applications,
        'today_applications': today_applications,
        'week_applications': week_applications,
        'month_applications': month_applications,
        'status_counts': {
            'SUBMITTED': submitted_count,
            'UNDER_REVIEW': under_review_count,
            'DOCUMENTS_REQUIRED': docs_required_count,
            'APPROVED': approved_count,
            'ENROLLED': enrolled_count,
            'REJECTED': rejected_count,
            'WITHDRAWN': withdrawn_count,
            'DRAFT': draft_count,
            'queue': queue_count,
        },
        'budget_stats': {
            'places': total_budget_places,
            'applications': budget_apps_count,
            'approved': budget_approved_count,
            'enrolled': budget_enrolled_count,
            'fill_rate': budget_fill_rate,
            'competition': budget_competition,
            'share': budget_share,
        },
        'paid_stats': {
            'places': total_paid_places,
            'applications': paid_apps_count,
            'approved': paid_approved_count,
            'enrolled': paid_enrolled_count,
            'fill_rate': paid_fill_rate,
            'competition': paid_competition,
            'share': paid_share,
        },
        'overall_stats': {
            'total_places': total_planned_places,
            'total_enrolled': total_enrolled_all,
            'fill_rate': overall_fill_rate,
            'competition': overall_competition,
        },
        'funnel': {
            'stage_registered': stage_registered,
            'stage_applied': stage_applied,
            'stage_with_docs': stage_with_docs,
            'stage_approved': stage_approved,
            'stage_enrolled': stage_enrolled,
            'conv_reg_to_app': conv_reg_to_app,
            'conv_app_to_docs': conv_app_to_docs,
            'conv_docs_to_appr': conv_docs_to_appr,
            'conv_appr_to_enr': conv_appr_to_enr,
            'overall_conversion': overall_conversion,
        },
        'financial': {
            'enrolled_paid_revenue': enrolled_paid_revenue,
            'pipeline_paid_revenue': pipeline_paid_revenue,
            'avg_annual_tuition': avg_annual_tuition,
        },
        'scores': {
            'avg_total': avg_total_score,
            'avg_budget': avg_budget_score,
            'avg_paid': avg_paid_score,
            'originals_count': verified_edu_docs_count,
            'originals_percentage': verified_edu_percentage,
        },
        'operations': {
            'total_users': total_users_count,
            'total_officers': total_officers_count,
            'unverified_docs': unverified_docs_count,
            'verified_docs_percent': verified_docs_percent,
            'new_feedback': new_feedback_count,
            'in_progress_feedback': in_progress_feedback_count,
            'total_feedback': total_feedback_count,
        },
        'faculty_stats': faculty_stats,
        'top_specialties': top_specialties,
        'study_forms_stat': study_forms_stat,
        'recent_logs': recent_logs,
        'charts_json': json.dumps(charts_json, ensure_ascii=False, cls=DjangoJSONEncoder),
        'breadcrumbs': breadcrumbs,
        'current_time': now,
    }

    return render(request, 'admin/dashboard.html', context)



