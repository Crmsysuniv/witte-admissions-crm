from django.urls import resolve, Resolver404

PATH_TITLES = {
    # System & Auth
    'admin': 'Панель управления',
    'accounts': 'Пользователи',
    'user': 'Пользователи',
    'login': 'Вход в систему',
    'register': 'Регистрация абитуриента',
    'logout': 'Выход',
    'password_change': 'Смена пароля',
    'student': 'Кабинет абитуриента',
    'officer': 'Приемная комиссия',
    'workplace': 'Рабочий стол сотрудника',
    'dashboard': 'Дашборд',
    'profile': 'Персональные данные',
    'apply': 'Подача заявления',
    'documents': 'Документы и сканы',
    'rating': 'Конкурсные списки и рейтинг',
    'withdraw': 'Отзыв заявления',
    
    # Admissions
    'admissions': 'Приемная комиссия',
    'faculties': 'Факультеты и институты',
    'programs': 'Программы обучения',
    'specialties': 'Направления подготовки',
    'rules': 'Правила приема и документы',
    'calculator': 'Калькулятор баллов ЕГЭ',
    'tuition': 'Стоимость и скидки',
    'dormitory': 'Общежитие и кампус',
    'campus': 'Студенческий городок',
    'faq': 'Часто задаваемые вопросы (FAQ)',
    'contacts': 'Контакты и схема проезда',
    'application': 'Заявления',
    'applicantprofile': 'Профили абитуриентов',
    'officerprofile': 'Профили сотрудников',
    'faculty': 'Факультеты',
    'specialty': 'Направления подготовки',
    'educationprogram': 'Программы обучения',
    'examsubject': 'Предметы ЕГЭ / ВИ',
    'applicationdocument': 'Документы абитуриентов',
    'examscore': 'Баллы вступительных испытаний',
    
    # Feedback & Audit
    'feedback': 'Обратная связь',
    'feedbackmessage': 'Сообщения',
    'audit': 'Аудит системы',
    'statuslog': 'История статусов',
    'notification': 'Уведомления',
    
    # Actions
    'add': 'Добавление',
    'change': 'Редактирование',
    'delete': 'Удаление',
    'history': 'История изменений',
}


def breadcrumbs_processor(request):
    """
    Контекстный процессор для динамических хлебных крошек (breadcrumbs).
    Автоматически строит иерархию пути на основе URL или явно переданного request.breadcrumbs.
    """
    if hasattr(request, 'breadcrumbs') and request.breadcrumbs:
        return {'breadcrumbs': request.breadcrumbs}

    breadcrumbs = [
        {'title': 'Главная', 'url': '/', 'is_active': False}
    ]

    path = request.path.strip('/')
    if not path:
        breadcrumbs[0]['is_active'] = True
        return {'breadcrumbs': breadcrumbs}

    segments = path.split('/')
    accumulated_path = ''

    for index, segment in enumerate(segments):
        accumulated_path += f'/{segment}'
        is_last = (index == len(segments) - 1)

        if segment.isdigit():
            title = f"Запись №{segment}"
        else:
            segment_lower = segment.lower()
            title = PATH_TITLES.get(segment_lower, segment.replace('_', ' ').replace('-', ' ').capitalize())

        breadcrumbs.append({
            'title': title,
            'url': f"{accumulated_path}/",
            'is_active': is_last
        })

    return {'breadcrumbs': breadcrumbs}
