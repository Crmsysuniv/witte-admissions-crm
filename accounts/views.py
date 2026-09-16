from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import login
from .forms import ApplicantRegistrationForm


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
