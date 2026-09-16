from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.utils.http import url_has_allowed_host_and_scheme
from .models import User
from .forms import ApplicantRegistrationForm, LoginForm, CustomPasswordChangeForm


def get_redirect_url_for_role(user, next_url=None, request=None):
    """
    Определяет целевой URL перенаправления после авторизации в зависимости от роли пользователя.
    1. Администратор (ADMIN) -> Панель управления /admin/
    # 2. Сотрудник приемной комиссии (OFFICER) -> Рабочее место сотрудника /officer/workplace/
    # 3. Абитуриент (APPLICANT) -> Главная страница портала абитуриента /student/dashboard/
    """
    # Если передан корректный и безопасный URL в параметре next, отдаем ему приоритет
    if next_url and request and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
        excluded_paths = ['/login/', '/logout/', '/register/', '/accounts/login/', '/accounts/logout/', '/accounts/register/']
        if next_url not in excluded_paths:
            return next_url

    # Перенаправление по роли
    if user.role == User.Role.ADMIN or user.is_superuser:
        return '/admin/dashboard/'
    elif user.role == User.Role.OFFICER:
        return '/officer/workplace/'
    elif user.role == User.Role.APPLICANT:
        return '/student/dashboard/'

    return '/'


def login_view(request):
    """
    Контроллер авторизации пользователей с перенаправлением в зависимости от роли.
    Поддерживает вход по логину или email, опцию «Запомнить меня» и возврат на исходную страницу (next).
    """
    next_url = request.POST.get('next') or request.GET.get('next', '')

    if request.user.is_authenticated:
        messages.info(
            request,
            f'Вы уже авторизованы в системе под именем {request.user.get_full_name() or request.user.username} '
            f'(роль: {request.user.get_role_display()}).'
        )
        return redirect(get_redirect_url_for_role(request.user, next_url, request))

    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)

            # Настройка времени жизни сессии («Запомнить меня»)
            if form.cleaned_data.get('remember_me'):
                request.session.set_expiry(1209600)  # 2 недели
            else:
                request.session.set_expiry(0)  # До закрытия браузера

            # Персонализированное приветственное Flash-сообщение в зависимости от роли
            if user.role == User.Role.ADMIN or user.is_superuser:
                messages.success(
                    request,
                    f'Добро пожаловать в панель администратора CRM, {user.get_full_name() or user.username}!'
                )
            elif user.role == User.Role.OFFICER:
                messages.success(
                    request,
                    f'Здравствуйте, {user.get_full_name() or user.username}! '
                    'Открыто рабочее место сотрудника приемной комиссии МУ им. С.Ю. Витте.'
                )
            else:
                messages.success(
                    request,
                    f'Добро пожаловать в личный кабинет абитуриента, {user.get_full_name() or user.username}!'
                )

            redirect_target = get_redirect_url_for_role(user, next_url, request)
            return redirect(redirect_target)
        else:
            messages.error(
                request,
                'Не удалось войти в систему. Пожалуйста, проверьте правильность введенного логина (или email) и пароля.'
            )
    else:
        form = LoginForm()

    context = {
        'form': form,
        'next': next_url,
    }
    return render(request, 'login.html', context)


def logout_view(request):
    """
    Контроллер выхода из системы с перенаправлением и уведомлением в зависимости от роли.
    - Сотрудники комиссии и Администраторы перенаправляются на страницу входа (/login/)
    - Абитуриенты перенаправляются на главную страницу портала (/)
    """
    user_role = None
    user_name = ''

    if request.user.is_authenticated:
        user_role = request.user.role
        user_name = request.user.get_full_name() or request.user.username

    logout(request)

    # Ролевое перенаправление после завершения сеанса
    if user_role in [User.Role.ADMIN, User.Role.OFFICER]:
        messages.info(
            request,
            f'Сеанс работы сотрудника ({user_name}) успешно завершен. Для повторного доступа авторизуйтесь в системе.'
        )
        return redirect('login')
    else:
        messages.success(
            request,
            'Вы успешно вышли из личного кабинета абитуриента. Будем рады видеть вас снова!'
        )
        return redirect('home')


def register_view(request):
    """
    Контроллер самостоятельной регистрации абитуриента в CRM МУ им. С.Ю. Витте.
    
    1. Проверяет надежность пароля (длина, регистры, цифры, спецсимволы).
    2. Автоматически присваивает пользователю роль APPLICANT.
    3. Создает связанную запись ApplicantProfile.
    4. Автоматически авторизует нового абитуриента и выводит Flash-уведомление.
    """
    if request.user.is_authenticated:
        messages.info(request, 'Вы уже авторизованы в системе.')
        return redirect('home')

    if request.method == 'POST':
        form = ApplicantRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()

            # Автоматическая авторизация нового абитуриента после успешной регистрации
            login(request, user)

            messages.success(
                request,
                f'Добро пожаловать в личный кабинет абитуриента, {user.first_name or user.username}! '
                'Ваша учетная запись успешно создана с ролью «Абитуриент». '
                'Теперь вы можете подавать заявления, загружать документы и отслеживать конкурсные списки.'
            )
            return redirect('home')
        else:
            messages.error(
                request,
                'Не удалось завершить регистрацию. Пожалуйста, проверьте правильность заполненных полей и требования к надежности пароля.'
            )
    else:
        form = ApplicantRegistrationForm()

    context = {
        'form': form,
    }
    return render(request, 'register.html', context)


@login_required
def password_change_view(request):
    """
    Контроллер безопасной самостоятельной смены пароля для всех авторизованных пользователей CRM
    (Абитуриенты, Сотрудники приемной комиссии, Администраторы).
    
    1. Проверяет корректность старого пароля учетной записи.
    2. Выполняет комплексную проверку надежности нового пароля (длина, регистры, цифры, спецсимволы).
    3. Проверяет несовпадение нового пароля со старым.
    4. Сохраняет обновленный хеш пароля в базе данных.
    5. Обновляет сессионный хеш аутентификации (update_session_auth_hash), предотвращая разлогинивание.
    6. Выводит персонализированное Flash-сообщение об успехе.
    """
    if request.method == 'POST':
        form = CustomPasswordChangeForm(user=request.user, data=request.POST)
        if form.is_valid():
            user = form.save()
            # Обновляем сессионный хеш, чтобы сессия пользователя оставалась активной
            update_session_auth_hash(request, user)

            messages.success(
                request,
                'Пароль вашей учетной записи успешно обновлен и защищен! '
                'Сессия авторизации сохранена. Используйте новый пароль при следующем входе в систему.'
            )
            return redirect('password_change')
        else:
            messages.error(
                request,
                'Не удалось изменить пароль. Пожалуйста, проверьте правильность действующего пароля и требования к новому паролю.'
            )
    else:
        form = CustomPasswordChangeForm(user=request.user)

    context = {
        'form': form,
    }
    return render(request, 'password_change.html', context)

