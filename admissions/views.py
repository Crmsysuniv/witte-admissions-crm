import json
from django.shortcuts import render, get_object_or_404
from django.db.models import Q, Count
from django.core.serializers.json import DjangoJSONEncoder
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


def admissions_rules(request):
    """
    Страница «Правила приема и нормативные документы» МУ им. С.Ю. Витте.
    """
    documents_categories = [
        {
            'category': 'Основные документы вуза',
            'icon': 'bi-shield-check',
            'color': 'indigo',
            'items': [
                {
                    'title': 'Устав ОЧУ ВО «Московский университет имени С.Ю. Витте»',
                    'date': '15.01.2024',
                    'number': 'Приказ №12-ОД',
                    'type': 'PDF',
                    'size': '2.4 МБ',
                },
                {
                    'title': 'Лицензия на осуществление образовательной деятельности (с бессрочными приложениями)',
                    'date': '20.08.2015',
                    'number': '№ 1618, серия 90Л01 № 0008608',
                    'type': 'PDF',
                    'size': '1.8 МБ',
                },
                {
                    'title': 'Свидетельство о государственной аккредитации образовательной деятельности',
                    'date': '18.12.2020',
                    'number': '№ 3469, серия 90А01 № 0003714',
                    'type': 'PDF',
                    'size': '3.1 МБ',
                },
            ]
        },
        {
            'category': 'Нормативные акты приемной кампании 2026/2027',
            'icon': 'bi-file-earmark-ruled',
            'color': 'blue',
            'items': [
                {
                    'title': 'Правила приема на обучение по программам бакалавриата и магистратуры на 2026/2027 уч. год',
                    'date': '01.11.2025',
                    'number': 'Утв. ректором МУ им. С.Ю. Витте',
                    'type': 'PDF',
                    'size': '4.2 МБ',
                },
                {
                    'title': 'Правила приема на обучение в Колледж МУ им. С.Ю. Витте (программы СПО) на 2026/2027 уч. год',
                    'date': '01.11.2025',
                    'number': 'Приказ №108-ОД',
                    'type': 'PDF',
                    'size': '1.9 МБ',
                },
                {
                    'title': 'Перечень вступительных испытаний с указанием минимальных баллов и приоритетности предметов',
                    'date': '01.11.2025',
                    'number': 'Приложение №1 к Правилам приема',
                    'type': 'PDF',
                    'size': '850 КБ',
                },
                {
                    'title': 'Порядок учета индивидуальных достижений поступающих (ГТО, золотая медаль, олимпиады)',
                    'date': '01.11.2025',
                    'number': 'Приложение №2 к Правилам приема',
                    'type': 'PDF',
                    'size': '620 КБ',
                },
            ]
        },
        {
            'category': 'Квоты, особые права и целевое обучение',
            'icon': 'bi-award',
            'color': 'emerald',
            'items': [
                {
                    'title': 'Положение о приеме лиц, имеющих особые права и преимущества при зачислении',
                    'date': '10.11.2025',
                    'number': 'Приказ №115-ОД',
                    'type': 'PDF',
                    'size': '1.1 МБ',
                },
                {
                    'title': 'Квота приема на целевое обучение по программам высшего образования на 2026 год',
                    'date': '15.11.2025',
                    'number': 'Распоряжение ПК-04',
                    'type': 'PDF',
                    'size': '780 КБ',
                },
                {
                    'title': 'Порядок приема в пределах отдельной специальной квоты (участники СВО и их дети)',
                    'date': '20.11.2025',
                    'number': 'Приказ №121-ОД',
                    'type': 'PDF',
                    'size': '940 КБ',
                },
            ]
        },
        {
            'category': 'Платное обучение и бланки документов',
            'icon': 'bi-cash-coin',
            'color': 'amber',
            'items': [
                {
                    'title': 'Приказ об установлении стоимости обучения на 2026/2027 учебный год',
                    'date': '12.01.2026',
                    'number': 'Приказ №05-ОД',
                    'type': 'PDF',
                    'size': '1.5 МБ',
                },
                {
                    'title': 'Типовая форма договора об оказании платных образовательных услуг (2-х и 3-х сторонний)',
                    'date': '12.01.2026',
                    'number': 'Утвержденная форма',
                    'type': 'PDF',
                    'size': '520 КБ',
                },
                {
                    'title': 'Бланк согласия на обработку персональных данных абитуриента',
                    'date': '01.02.2026',
                    'number': 'Форма Ф-01',
                    'type': 'DOCX',
                    'size': '85 КБ',
                },
            ]
        },
    ]

    context = {
        'documents_categories': documents_categories,
    }
    return render(request, 'admissions_rules.html', context)


def score_calculator(request):
    """
    Интерактивный калькулятор проходных баллов ЕГЭ и подбор направлений обучения.
    """
    subjects = ExamSubject.objects.all()
    specialties = Specialty.objects.filter(is_active=True).select_related('faculty').prefetch_related('programs')

    # Specialty requirements map for accurate client-side and server-side calculation
    specialties_data = []
    for sp in specialties:
        # Determine required subjects based on specialty code/faculty
        if sp.code.startswith('09.'):
            required = ['Русский язык', 'Математика (профильная)']
            choice_subjects = ['Информатика и ИКТ', 'Физика']
            min_sum = 123
        elif sp.code.startswith('40.'):
            required = ['Русский язык', 'Обществознание']
            choice_subjects = ['История', 'Информатика и ИКТ', 'Иностранный язык (английский)']
            min_sum = 117
        elif sp.code.startswith('42.'):
            required = ['Русский язык', 'Обществознание']
            choice_subjects = ['История', 'Иностранный язык (английский)']
            min_sum = 112
        else: # 38. Economics, Management, State management
            required = ['Русский язык', 'Математика (профильная)']
            choice_subjects = ['Обществознание', 'Информатика и ИКТ', 'История', 'Иностранный язык (английский)']
            min_sum = 121

        specialties_data.append({
            'id': sp.id,
            'code': sp.code,
            'name': sp.name,
            'faculty': sp.faculty.name,
            'level': sp.get_education_level_display(),
            'budget_places': sp.budget_places,
            'paid_places': sp.paid_places,
            'min_sum': min_sum,
            'required': required,
            'choice_subjects': choice_subjects,
            'programs_count': sp.programs.count(),
        })

    subjects_data = [
        {'id': s.id, 'name': s.name, 'min_score': s.min_score}
        for s in subjects
    ]

    context = {
        'subjects': subjects,
        'specialties': specialties,
        'specialties_data': specialties_data,
        'specialties_json': json.dumps(specialties_data, ensure_ascii=False, cls=DjangoJSONEncoder),
        'subjects_json': json.dumps(subjects_data, ensure_ascii=False, cls=DjangoJSONEncoder),
    }
    return render(request, 'score_calculator.html', context)


def tuition_fees(request):
    """
    Страница «Стоимость и скидки на обучение» МУ им. С.Ю. Витте.
    Каталог программ с ценами, калькулятор рассрочки/кредита, программы скидок.
    """
    programs = EducationProgram.objects.filter(is_active=True).select_related(
        'specialty', 'specialty__faculty'
    ).order_by('specialty__faculty__name', 'specialty__code', 'study_form')

    faculties = Faculty.objects.all()

    programs_json_data = []
    for p in programs:
        fee_float = float(p.tuition_fee)
        semester_fee = round(fee_float / 2)
        month_installment = round(fee_float / 10)
        programs_json_data.append({
            'id': p.id,
            'specialty_code': p.specialty.code,
            'specialty_name': p.specialty.name,
            'faculty_id': p.specialty.faculty_id,
            'faculty_name': p.specialty.faculty.name,
            'level': p.specialty.education_level,
            'level_display': p.specialty.get_education_level_display(),
            'study_form': p.study_form,
            'study_form_display': p.get_study_form_display(),
            'duration': p.duration,
            'fee_annual': fee_float,
            'fee_semester': semester_fee,
            'fee_month': month_installment,
        })

    discount_categories = [
        {
            'title': 'Скидки по баллам ЕГЭ и результатам олимпиад',
            'icon': 'bi-award-fill',
            'color': 'indigo',
            'items': [
                {
                    'name': '240 баллов и выше по сумме 3-х ЕГЭ',
                    'discount': '20%',
                    'description': 'Предоставляется на 1-й год обучения. Со 2-го курса сохраняется при сдаче сессий на «отлично».',
                    'badge': 'Максимальная скидка',
                },
                {
                    'name': 'От 200 до 239 баллов по сумме ЕГЭ',
                    'discount': '15%',
                    'description': 'Предоставляется на 1-й год обучения поступающим на очную и очно-заочную форму.',
                    'badge': 'Популярная',
                },
                {
                    'name': 'От 180 до 199 баллов по сумме ЕГЭ',
                    'discount': '10%',
                    'description': 'Предоставляется на первый семестр обучения с возможностью продления по итогам сессии.',
                    'badge': 'Базовая',
                },
                {
                    'name': 'Победители и призеры олимпиад школьников',
                    'discount': '20%',
                    'description': 'Для участников заключительных этапов олимпиад из перечня Минобрнауки РФ.',
                    'badge': 'Таланты',
                },
            ]
        },
        {
            'title': 'Корпоративные скидки и преемственность образования',
            'icon': 'bi-buildings-fill',
            'color': 'blue',
            'items': [
                {
                    'name': 'Выпускники Колледжа МУ им. С.Ю. Витте',
                    'discount': '15%',
                    'description': 'Фиксированная скидка 15% на весь период обучения по программам высшего образования (бакалавриат).',
                    'badge': 'Для выпускников СПО',
                },
                {
                    'name': 'Выпускники бакалавриата Витте в магистратуру',
                    'discount': '15%',
                    'description': 'Скидка на все магистерские программы университета при непрерывном продолжении обучения.',
                    'badge': 'Магистратура',
                },
                {
                    'name': 'Сотрудники компаний-партнеров университета',
                    'discount': '10%',
                    'description': 'Действует для сотрудников Сбера, ВТБ, VK, КонсультантПлюс и других стратегических партнеров вуза.',
                    'badge': 'Партнерская',
                },
            ]
        },
        {
            'title': 'Социальные и семейные программы поддержки',
            'icon': 'bi-heart-fill',
            'color': 'emerald',
            'items': [
                {
                    'name': 'Участники СВО и их дети',
                    'discount': '20%',
                    'description': 'Специальная университетская мера социальной поддержки на весь нормативный срок обучения.',
                    'badge': 'Господдержка',
                },
                {
                    'name': 'Семейная скидка «Учимся вместе»',
                    'discount': '10%',
                    'description': 'При одновременном обучении в университете или колледже двух и более членов одной семьи (братья, сестры, родители).',
                    'badge': 'Семейная',
                },
                {
                    'name': 'Дети-сироты и инвалиды I, II групп',
                    'discount': '15%',
                    'description': 'Социальная льгота при поступлении на договорную форму обучения сверх установленных бюджетных квот.',
                    'badge': 'Социальная',
                },
            ]
        },
    ]

    context = {
        'programs': programs,
        'faculties': faculties,
        'programs_json': json.dumps(programs_json_data, ensure_ascii=False, cls=DjangoJSONEncoder),
        'discount_categories': discount_categories,
    }
    return render(request, 'tuition_fees.html', context)


def dormitory_info(request):
    """
    Страница «Общежитие и студенческий городок» МУ им. С.Ю. Витте.
    """
    buildings = [
        {
            'id': 1,
            'title': 'Студенческий комплекс «Автозаводский»',
            'address': 'г. Москва, 2-й Кожуховский проезд, д. 12, стр. 1',
            'metro': 'м. Автозаводская / МЦК ЗИЛ (7-10 мин пешком)',
            'type': 'Блочный тип',
            'capacity': '450 мест',
            'price_from': '6 500',
            'badge': 'Рядом с главным кампусом',
            'badge_color': 'emerald',
            'description': 'Удобное расположение в 3 минутах ходьбы от главного учебного корпуса университета. Блоки состоят из двух уютных комнат (на 2 и 3 человека) с отдельным санузлом и душевой кабиной.',
            'features': [
                'Кухни на каждом этаже с индукционными плитами и микроволновками',
                'Бесплатные прачечные со стиральными и сушильными машинами',
                'Коворкинг и комната самоподготовки с Wi-Fi 200 Мбит/с',
                'Круглосуточный пост охраны, видеонаблюдение и электронный доступ (СКУД)',
            ],
            'rooms': [
                {'type': '3-местное размещение', 'price': '6 500 руб./мес.'},
                {'type': '2-местное размещение', 'price': '7 800 руб./мес.'},
            ]
        },
        {
            'id': 2,
            'title': 'Университетский кампус «Нагатинский»',
            'address': 'г. Москва, проспект Андропова, д. 22',
            'metro': 'м. Коломенская / м. Технопарк (10-12 мин пешком)',
            'type': 'Квартирно-секционный тип',
            'capacity': '320 мест',
            'price_from': '8 900',
            'badge': 'Повышенный комфорт',
            'badge_color': 'blue',
            'description': 'Современное общежитие квартирного типа с панорамным видом на Москву-реку и парк «Коломенское». В каждой квартире: изолированные спальни, собственная просторная кухня и раздельный санузел.',
            'features': [
                'Собственная кухня с холодильником и гарнитуром в каждой секции',
                'Тренажерный зал и зал групповых занятий для проживающих',
                'Закрытая охраняемая территория со спортивной воркаут-площадкой',
                'Кафе-столовая на первом этаже со скидками для студентов',
            ],
            'rooms': [
                {'type': '3-местная комната в секции', 'price': '8 900 руб./мес.'},
                {'type': '2-местная комната в секции', 'price': '10 500 руб./мес.'},
                {'type': '1-местная комната (студия)', 'price': '14 000 руб./мес.'},
            ]
        },
        {
            'id': 3,
            'title': 'Партнерский комплекс «Дубровка»',
            'address': 'г. Москва, ул. Шарикоподшипниковская, д. 13',
            'metro': 'м. Дубровка / м. Волгоградский проспект (5 мин пешком)',
            'type': 'Отельный тип / Апартаменты',
            'capacity': '180 мест',
            'price_from': '12 500',
            'badge': 'Для магистрантов и аспирантов',
            'badge_color': 'indigo',
            'description': 'Комфортабельные апартаменты гостиничного уровня для студентов старших курсов, магистрантов и преподавателей. Стильный дизайн комнат, клининг мест общего пользования и развитая инфраструктура.',
            'features': [
                'Кондиционирование и индивидуальный климат-контроль в номерах',
                'Еженедельная смена постельного белья и клининг',
                'Лаундж-зона с настольными играми и кинопроектором',
                'Подземный паркинг и зона каршеринга у здания',
            ],
            'rooms': [
                {'type': '2-местный номер стандарт', 'price': '12 500 руб./мес.'},
                {'type': '1-местный номер комфорт', 'price': '18 000 руб./мес.'},
            ]
        },
    ]

    campus_facilities = [
        {
            'title': 'Главный образовательный кампус',
            'icon': 'bi-mortarboard-fill',
            'color': 'blue',
            'description': 'Современные мультимедийные лекционные аудитории, компьютерные лаборатории с профессиональным ПО, анатомический и криминалистический полигоны.',
        },
        {
            'title': 'Библиотечно-информационный центр',
            'icon': 'bi-book-half',
            'color': 'indigo',
            'description': 'Фонд из более 150 000 печатных книг, доступ к ведущим электронным базам Znanium, IPR Smart, Юрайт и тихие зоны для продуктивной учебы.',
        },
        {
            'title': 'Спортивно-оздоровительный комплекс',
            'icon': 'bi-trophy-fill',
            'color': 'amber',
            'description': 'Универсальный игровой зал для баскетбола и волейбола, тренажерный зал с силовыми и кардиотренажерами, секции единоборств и йоги.',
        },
        {
            'title': 'Студенческое кафе и столовая',
            'icon': 'bi-cup-hot-fill',
            'color': 'emerald',
            'description': 'Качественное сбалансированное трехразовое питание, бизнес-ланчи от 250 руб., собственная выпечка, кофе-зоны и вендинговые автоматы.',
        },
        {
            'title': 'Медиацентр и молодежный коворкинг',
            'icon': 'bi-camera-reels-fill',
            'color': 'purple',
            'description': 'Студия звукозаписи, фото- и видеопродакшн «Витте Медиа», штаб-квартира Студенческого совета, КВН и волонтерского корпуса.',
        },
        {
            'title': 'Медицинский кабинет и психологическая служба',
            'icon': 'bi-heart-pulse-fill',
            'color': 'rose',
            'description': 'Первичная доврачебная помощь, вакцинация, диспансеризация и бесплатные конфиденциальные консультации квалифицированных психологов.',
        },
    ]

    context = {
        'buildings': buildings,
        'campus_facilities': campus_facilities,
    }
    return render(request, 'dormitory.html', context)


def export_rating_xlsx(request):
    """
    Экспорт рейтингового конкурсного списка по образовательной программе в файл .xlsx.
    Принимает параметры:
    - program (ID программы) или specialty (ID специальности);
    - financing (BUDGET или PAID);
    - originals (1 - только с оригиналами).
    """
    from .exports import export_rating_xlsx_response
    from .models import Application

    program_id = request.GET.get('program') or request.GET.get('program_id')
    specialty_id = request.GET.get('specialty') or request.GET.get('specialty_id')
    financing_type = request.GET.get('financing', Application.FinancingType.BUDGET)
    only_originals = request.GET.get('originals') in ['1', 'true', 'True']

    selected_program = None
    if program_id and str(program_id).isdigit():
        selected_program = EducationProgram.objects.filter(id=program_id, is_active=True).first()
    elif specialty_id and str(specialty_id).isdigit():
        selected_program = EducationProgram.objects.filter(specialty_id=specialty_id, is_active=True).first()

    if not selected_program:
        selected_program = EducationProgram.objects.filter(is_active=True).select_related('specialty__faculty').first()

    if not selected_program:
        from django.http import HttpResponseBadRequest
        return HttpResponseBadRequest("Нет активных программ для экспорта.")

    is_officer = request.user.is_authenticated and (
        getattr(request.user, 'role', '') == 'OFFICER' or request.user.is_staff or request.user.is_superuser
    )

    return export_rating_xlsx_response(
        program=selected_program,
        financing_type=financing_type,
        only_originals=only_originals,
        is_officer=is_officer
    )


