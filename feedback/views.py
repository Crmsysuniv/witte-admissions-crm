import json
from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from .models import FeedbackMessage
from .forms import FeedbackForm


def feedback_view(request):
    """
    Публичная страница формы обратной связи приемной комиссии МУ им. С.Ю. Витте.
    Отображает форму, обрабатывает GET-параметры (предзаполнение темы/контактов),
    а также выводит Flash-оповещения и информационный баннер успешно доставленного обращения.
    """
    # Если на /feedback/ отправлен POST-запрос напрямую, направляем в обработчик отправки
    if request.method == 'POST':
        return feedback_submit_view(request)

    # Проверяем, было ли обращение успешно отправлено (ID извлекается из сессии после PRG-редиректа)
    submitted_id = request.session.pop('last_submitted_inquiry_id', None)
    submitted_message = None
    if submitted_id:
        submitted_message = FeedbackMessage.objects.filter(id=submitted_id).first()

    initial_data = {}
    # Предзаполнение темы из query params (?subject=...)
    subject_param = request.GET.get('subject', '').strip()
    if subject_param:
        initial_data['subject'] = subject_param

    # Предзаполнение данных заявителя, если пользователь авторизован в системе
    if request.user.is_authenticated:
        initial_data['full_name'] = request.user.get_full_name() or request.user.username
        initial_data['email'] = request.user.email
        if hasattr(request.user, 'phone') and request.user.phone:
            initial_data['phone'] = request.user.phone

    form = FeedbackForm(initial=initial_data)

    context = {
        'form': form,
        'submitted_message': submitted_message,
    }
    return render(request, 'feedback_form.html', context)


def feedback_submit_view(request):
    """
    Обработчик отправки формы обратной связи с выводом Flash-сообщений
    об успешной доставке обращения в приемную комиссию.
    
    Поддерживает:
    1. Стандартный POST-запрос с Post-Redirect-Get (PRG) для предотвращения повторной отправки.
    2. Вывод Flash-сообщений через django.contrib.messages (success/error).
    3. Асинхронные AJAX/Fetch запросы с возвратом JSON и статуса доставки.
    """
    if request.method != 'POST':
        return redirect('feedback:feedback_form')

    form = FeedbackForm(request.POST)
    is_ajax = (
        request.headers.get('X-Requested-With') == 'XMLHttpRequest' or
        'application/json' in request.headers.get('Accept', '')
    )

    if form.is_valid():
        feedback = form.save(commit=False)
        feedback.status = FeedbackMessage.Status.NEW
        feedback.save()

        # Формируем информативное Flash-сообщение об успешной доставке в комиссию
        success_message = (
            f"Ваше обращение №{feedback.id} успешно доставлено в приемную комиссию МУ им. С.Ю. Витте! "
            f"Специалист рассмотрит его и направит официальный ответ на почту {feedback.email} в течение 2–4 рабочих часов."
        )
        messages.success(request, success_message)

        if is_ajax:
            return JsonResponse({
                'status': 'success',
                'id': feedback.id,
                'full_name': feedback.full_name,
                'email': feedback.email,
                'subject': feedback.subject,
                'created_at': feedback.created_at.strftime('%d.%m.%Y в %H:%M'),
                'message': success_message,
            })

        # Сохраняем ID в сессию для отображения детального баннера-квитанции после редиректа
        request.session['last_submitted_inquiry_id'] = feedback.id
        return redirect('feedback:feedback_form')

    else:
        # При ошибках валидации выводим Flash-сообщение об ошибке
        error_message = 'Не удалось доставить обращение. Пожалуйста, проверьте правильность заполненных полей формы.'
        messages.error(request, error_message)

        if is_ajax:
            return JsonResponse({
                'status': 'error',
                'message': error_message,
                'errors': form.errors.get_json_data(),
            }, status=400)

        # Рендерим форму с отображением ошибок валидации
        context = {
            'form': form,
            'submitted_message': None,
        }
        return render(request, 'feedback_form.html', context, status=400)

